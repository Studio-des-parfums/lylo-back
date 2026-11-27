import asyncio
import json
import logging
import os
import random
import time as _boot_time

import httpx
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import Agent, AgentSession, JobContext, JobProcess, WorkerOptions, cli, function_tool
from livekit.plugins import bey, cartesia, deepgram, openai, silero

from app.agent.brands.registry import get_brand_profile
from app.agent.builder import get_prompt
from app.agent import questionnaire_flow as flow
from app.agent import speech
from app.agent import profile_validation
from app.agent.i18n import err, t
from app.agent.prompts import guide as guide_prompts
from app.agent.state import AgentPhase, SessionState
from app.config import get_settings
from app.core.languages import SupportedLanguage

# LiveKit SDK reads LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
# directly from os.environ — load_dotenv() is required here
load_dotenv()

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lylo.agent")
logger.info("=== Agent module loaded at boot ===")

BEY_AVATAR_MALE_MODELS = [
    m for m in [
        os.getenv("BEY_AVATAR_MALE_MODEL_1"),
        os.getenv("BEY_AVATAR_MALE_MODEL_2"),
    ] if m
]

BEY_AVATAR_FEMALE_MODELS = [
    m for m in [
        os.getenv("BEY_AVATAR_FEMALE_MODEL_1"),
        os.getenv("BEY_AVATAR_FEMALE_MODEL_2"),
        os.getenv("BEY_AVATAR_FEMALE_MODEL_3"),
    ] if m
]


def pick_avatar(gender: str) -> str:
    models = BEY_AVATAR_FEMALE_MODELS if gender == "female" else BEY_AVATAR_MALE_MODELS
    if not models:
        fallback = BEY_AVATAR_FEMALE_MODELS or BEY_AVATAR_MALE_MODELS
        if not fallback:
            raise ValueError(f"Aucun avatar Bey configuré pour le genre '{gender}' — vérifiez BEY_AVATAR_MALE_MODEL_* / BEY_AVATAR_FEMALE_MODEL_* dans .env")
        logger.warning(f"[AVATAR] Aucun avatar pour genre='{gender}', fallback sur l'autre genre")
        models = fallback
    return random.choice(models)


# ─────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────

async def entrypoint(ctx: JobContext):
    import time as _time

    logger.info(f"[JOB] ✅ Job reçu — room={ctx.room.name} job_id={ctx.job.id} PID={os.getpid()} at {_time.time():.3f}")
    logger.debug(f"[JOB] Détails job: {ctx.job}")

    logger.info("[CONNECT] Connexion à la room LiveKit...")
    try:
        await ctx.connect()
        logger.info(f"[CONNECT] ✅ Connecté à la room {ctx.room.name} — participants: {len(ctx.room.remote_participants)}")
    except Exception as e:
        logger.exception(f"[CONNECT] ❌ Erreur connexion room: {e}")
        return

    session_id = ctx.room.name.replace("room_", "")
    logger.info(f"[SESSION_ID] session_id={session_id}")

    # Hooks de timing — mesurent la durée de CHAQUE appel HTTP fait vers le backend
    # (tool calls du LLM inclus) sans avoir à instrumenter chaque fonction séparément.
    # Utile pour diagnostiquer un délai de réponse inhabituel (ex: 2-3s perçus par
    # l'utilisateur) : on peut voir précisément si le temps part dans cet appel réseau
    # ou ailleurs (LLM, TTS, connexion utilisateur↔LiveKit).
    # Les event hooks d'un client httpx ASYNC doivent être des coroutines — une
    # fonction sync ici ferait `await None` et casserait silencieusement CHAQUE
    # requête (httpx attend le retour du hook).
    async def _log_request_start(request: httpx.Request):
        request.extensions["start_time"] = _boot_time.monotonic()

    async def _log_response_end(response: httpx.Response):
        start = response.request.extensions.get("start_time")
        elapsed_ms = (_boot_time.monotonic() - start) * 1000 if start else -1
        # `at=` en time.time() (horloge murale) pour rester comparable aux autres logs
        # du fichier ([AGENT_STATE], [GREETING], ...) qui utilisent tous _time.time().
        logger.info(
            f"[HTTP_TIMING] {response.request.method} {response.request.url.path} "
            f"→ {response.status_code} en {elapsed_ms:.0f}ms (at {_boot_time.time():.3f})"
        )

    http = httpx.AsyncClient(
        base_url=settings.backend_url,
        timeout=30.0,
        event_hooks={"request": [_log_request_start], "response": [_log_response_end]},
    )
    logger.info(f"[HTTP] Récupération session depuis {settings.backend_url}/api/session/{session_id}")

    # Backoff court et progressif plutôt qu'une attente fixe de 1s : la session est
    # généralement déjà prête côté backend en quelques centaines de ms (le frontend la
    # crée juste avant de faire rejoindre l'agent à la room) — un sleep(1.0) fixe fait
    # perdre jusqu'à ~850ms de latence de démarrage dans le cas normal. Le total cumulé
    # (~5.9s) reste proche de l'ancien (5s) pour ne pas perdre en robustesse sur les cas lents.
    retry_delays = [0.2, 0.4, 0.8, 1.5, 3.0]
    for attempt, delay in enumerate(retry_delays):
        try:
            resp = await http.get(f"/api/session/{session_id}")
            logger.info(f"[HTTP] Tentative {attempt + 1}/{len(retry_delays)} — status={resp.status_code}")
            if resp.status_code == 200:
                break
            logger.warning(f"[HTTP] Session {session_id} pas encore prête (attempt {attempt + 1}/{len(retry_delays)})")
        except Exception as e:
            logger.error(f"[HTTP] Tentative {attempt + 1}/{len(retry_delays)} — Erreur réseau: {e}")
        await asyncio.sleep(delay)
    else:
        logger.error(f"[HTTP] ❌ Session {session_id} introuvable après {len(retry_delays)} tentatives — agent abandonne.")
        await http.aclose()
        return

    config = resp.json()
    logger.info(f"[SESSION] Config reçue — language={config.get('language')} mode={config.get('mode')} input_mode={config.get('input_mode')} questions={len(config.get('questions', []))}")

    if "language" not in config or "questions" not in config:
        logger.error(f"[SESSION] ❌ Données incomplètes — clés reçues: {list(config.keys())}")
        await http.aclose()
        return

    logger.info(f"[SESSION] ✅ Session valide, démarrage de l'agent — room={ctx.room.name}")

    lang: SupportedLanguage = config.get("language", "fr")
    voice_gender = config.get("voice_gender", "female")
    ai_name = "Rose" if voice_gender == "female" else "Florian"
    input_mode = config.get("input_mode", "voice")
    brand = config.get("brand", "lylo")
    brand_profile = get_brand_profile(brand)
    answer_fmt = flow.answer_format(config)
    use_avatar = [config.get("avatar", True)]
    # Capacité annoncée par le client (ex. robot) : accompagner le visiteur jusqu'à ce lieu.
    guide_dest = guide_prompts.guide_destination(config)
    _first_tts_call = [True]

    # Machine à états
    state = SessionState()

    # Flags de contrôle
    paused = [False]
    user_interrupted = [False]

    # ─── Texte parlé : formes genrées des libellés (« solo/a », « seul(e) ») ──

    async def _spoken_text(text):
        """Le TTS lit littéralement « solo/a » : on remplace par la forme adaptée au genre.
        Le flux est découpé au dernier espace pour ne jamais couper « solo/ » | « a »."""
        buf = ""
        async for chunk in text:
            buf += chunk
            cut = buf.rfind(" ")
            if cut >= 0:
                yield speech.resolve_gender_forms(buf[:cut + 1], speech.is_feminine(state.profile.get("gender")))
                buf = buf[cut + 1:]
        if buf:
            yield speech.resolve_gender_forms(buf, speech.is_feminine(state.profile.get("gender")))

    # ─── Sous-classe agent avec override TTS et LLM ───────────────────────

    class StatefulAgent(Agent):
        def llm_node(self, chat_ctx, tools, model_settings):
            if paused[0]:
                return None
            return Agent.default.llm_node(self, chat_ctx, tools, model_settings)

        async def tts_node(self, text, model_settings):
            import time
            tts_call_id = id(text) % 100000
            logger.debug(f"[TTS_NODE:{tts_call_id}] called at {time.time():.3f}")

            sample_rate = 24000
            samples_per_channel = 480
            silence_data = bytes(samples_per_channel * 2)

            if use_avatar[0] and _first_tts_call[0]:
                _first_tts_call[0] = False
                warmup_frames = 100
                logger.debug(f"[TTS_NODE:{tts_call_id}] prepending {warmup_frames * 20}ms warmup silence")
                for _ in range(warmup_frames):
                    yield rtc.AudioFrame(
                        data=silence_data,
                        sample_rate=sample_rate,
                        num_channels=1,
                        samples_per_channel=samples_per_channel,
                    )

            frame_count = 0
            try:
                async for frame in Agent.default.tts_node(self, _spoken_text(text), model_settings):
                    if frame_count == 0:
                        logger.debug(f"[TTS_NODE:{tts_call_id}] FIRST real audio frame at {time.time():.3f}")
                    frame_count += 1
                    yield frame
            except Exception as e:
                logger.error(f"[TTS_NODE:{tts_call_id}] TTS error (Cartesia): {e}")

            if use_avatar[0]:
                for _ in range(25):
                    yield rtc.AudioFrame(
                        data=silence_data,
                        sample_rate=sample_rate,
                        num_channels=1,
                        samples_per_channel=samples_per_channel,
                    )
            logger.debug(f"[TTS_NODE:{tts_call_id}] done — {frame_count} frames")

    # ─── Envoi d'état au frontend ──────────────────────────────────────────

    async def send_state_update(payload: dict):
        try:
            await ctx.room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"),
                topic="state",
                reliable=True,
            )
        except Exception:
            pass

    # ─── Avancement d'état ─────────────────────────────────────────────────

    async def advance_to(new_phase: AgentPhase) -> str:
        old = state.phase
        state.phase = new_phase
        logger.info(f"[STATE] {old.name} → {new_phase.name}")
        if new_phase == AgentPhase.Q_FAVORITES and old != AgentPhase.Q_FAVORITES:
            # Cartes cliquables dès le début de la question, sans attendre que le LLM appelle
            # notify_asking_top_2 : il l'appelait parfois APRÈS avoir posé la question (voire
            # après la réponse orale) — impossible de cliquer pendant la 1re question.
            questions = config.get("questions", [])
            if state.current_question_index < len(questions):
                qid = questions[state.current_question_index]["id"]
                logger.info(f"[Q] step_asking_top_2 envoyé à l'entrée de l'étape q={qid}")
                await send_state_update({"type": "step_asking_top_2", "state": "questionnaire", "question_id": qid})
        prompt = get_prompt(state, config, ai_name, lang, input_mode)
        await agent.update_instructions(prompt)
        # Return a minimal acknowledgment — the LLM will generate its reply
        # from the updated system instructions, not from this tool result
        return "[ok]"

    # ─── Function tools ────────────────────────────────────────────────────

    @function_tool()
    async def save_user_profile(field: str, value: str):
        """Saves a user profile field. Call immediately when user provides: first_name, gender, age, pregnant, has_disliked_notes, disliked_notes, has_allergies, or allergies. / Sauvegarde un champ du profil utilisateur. Appeler immédiatement quand l'utilisateur fournit : first_name, gender, age, pregnant, has_disliked_notes, disliked_notes, has_allergies ou allergies."""
        # Étapes obligatoires : seul le champ de l'étape en cours, avec une valeur valide, fait
        # avancer. Un champ déjà renseigné peut être corrigé, sans changer d'étape.
        expected = profile_validation.EXPECTED_FIELD.get(state.phase)
        if field != expected and field not in state.profile:
            logger.warning(f"[PROFILE] refusé : {field} hors étape (state={state.phase.name}, attendu={expected})")
            return (f"[rejected] Wrong step: the current REQUIRED step is '{expected}'. Nothing was recorded. "
                    "Ask that question; never skip it.")
        value, refusal = profile_validation.validate(field, value)
        if refusal:
            logger.warning(f"[PROFILE] refusé : {field} invalide (state={state.phase.name})")
            return refusal
        is_correction = field != expected

        resp = await http.post(
            f"/api/session/{session_id}/save-profile",
            json={"field": field, "value": value},
        )
        data = resp.json() if resp.status_code == 200 else {}
        state.profile[field] = value
        logger.info(f"[PROFILE] Saved {field}={value} — state={state.phase.name}")

        await send_state_update({
            "type": "profile_update",
            "state": data.get("state", "collecting_profile"),
            "field": field,
            "value": value,
            "profile_complete": data.get("profile_complete", False),
            "missing_fields": data.get("missing_fields", []),
        })

        if is_correction:
            return f"[ok] {field} corrected. Now continue the current step ('{expected}')."

        # Transitions d'état selon le champ sauvegardé — retourne le prompt suivant
        if field == "first_name":
            return await advance_to(AgentPhase.GET_GENDER)
        elif field == "gender":
            return await advance_to(AgentPhase.GET_AGE)
        elif field == "age":
            if state.profile.get("gender") == "féminin":
                return await advance_to(AgentPhase.GET_PREGNANT)
            else:
                return await advance_to(AgentPhase.GET_DISLIKES)
        elif field == "pregnant":
            return await advance_to(AgentPhase.GET_DISLIKES)
        elif field == "has_disliked_notes":
            if value.lower() in ("oui", "yes"):
                return await advance_to(AgentPhase.GET_DISLIKE_DETAIL)
            else:
                return await advance_to(AgentPhase.GET_ALLERGIES)
        elif field == "disliked_notes":
            return await advance_to(AgentPhase.GET_ALLERGIES)
        elif field == "has_allergies":
            if value.lower() in ("oui", "yes"):
                return await advance_to(AgentPhase.GET_ALLERGY_DETAIL)
            else:
                await send_state_update({"type": "state_change", "state": "questionnaire"})
                return await advance_to(AgentPhase.Q_FAVORITES)
        elif field == "allergies":
            await send_state_update({"type": "state_change", "state": "questionnaire"})
            return await advance_to(AgentPhase.Q_FAVORITES)

        return t("profile_updated", lang, field=field, value=value)

    # ─── Questionnaire : l'étape suivante est décidée par le format (questionnaire_flow) ──

    async def _enter_question_step(question_id: int, phase: AgentPhase) -> str:
        """Notifie le frontend de l'étape qui commence, puis avance la machine à états."""
        if phase == AgentPhase.Q_LEAST:
            await send_state_update({
                "type": "step_asking_bottom_2",
                "state": "questionnaire",
                "question_id": question_id,
                "top_2": state.current_top_2,
            })
        elif phase == AgentPhase.Q_CONFIRM:
            await send_state_update({
                "type": "step_awaiting_confirmation",
                "state": "questionnaire",
                "question_id": question_id,
                "top_2": state.current_top_2,
                "bottom_2": state.current_bottom_2,
            })
        await advance_to(phase)
        return _next_step_hint(phase)

    def _next_step_hint(phase: AgentPhase) -> str:
        """Consigne explicite renvoyée par l'outil. advance_to() met à jour les instructions
        système, mais quand la phase ne change pas (2e justification : Q_JUSTIFY_POSITIVE →
        Q_JUSTIFY_POSITIVE) un simple "[ok]" laisse le LLM croire l'étape finie : il sautait
        la 2e justification et les choix « le moins »."""
        if phase == AgentPhase.Q_JUSTIFY_POSITIVE:
            choice = state.current_top_2[state.justify_index] if state.justify_index < len(state.current_top_2) else "?"
            return (f'[ok] Next step NOW: ask the user why they chose "{choice}" ({answer_fmt.positive_label}). '
                    "Then call justification_done. Do not skip this step.")
        if phase == AgentPhase.Q_JUSTIFY_NEGATIVE:
            choice = state.current_bottom_2[state.justify_index] if state.justify_index < len(state.current_bottom_2) else "?"
            return (f'[ok] Next step NOW: ask the user why they chose "{choice}" ({answer_fmt.negative_label}). '
                    "Then call justification_done. Do not skip this step.")
        if phase == AgentPhase.Q_LEAST:
            return (f"[ok] Next step NOW: ask for the {answer_fmt.negative_count} choice(s) "
                    f"{answer_fmt.negative_label}, then call notify_bottom_2. Do not skip this step.")
        if phase == AgentPhase.Q_CONFIRM:
            return "[ok] Next step NOW: recap the choices and ask for confirmation, then call save_answer."
        return "[ok]"

    def _choice_labels(question_id: int) -> list[str]:
        q = next((qq for qq in config["questions"] if qq["id"] == question_id), None)
        return [c["label"] if isinstance(c, dict) else c for c in (q or {}).get("choices", [])]

    async def _notify_top_2_now(question_id: int, top_2: list[str]) -> str:
        """Logique commune à l'outil notify_top_2 et au clic utilisateur (_handle_top_2_clicked) :
        enregistre les choix « le plus », notifie le frontend, passe à l'étape suivante."""
        # Numéro (« 4 ») ou libellé approximatif → libellé exact (sinon le front ne masque pas la carte)
        labels = _choice_labels(question_id)
        top_2 = flow.resolve_choices(top_2, labels)
        # Libellé inventé par le LLM (absent des cartes) : refusé plutôt qu'enregistré
        if unknown := flow.unknown_choices(top_2, labels):
            logger.warning(f"[Q] top_2 refusé, choix inconnu : {top_2}")
            return unknown
        # Nombre de choix imposé par le format (1 pour Help) : « le 1 et le 2 » est refusé
        mismatch = flow.count_mismatch(top_2, answer_fmt.positive_count, answer_fmt.positive_label)
        if mismatch:
            logger.warning(f"[Q] top_2 refusé : {len(top_2)} choix, attendu {answer_fmt.positive_count}")
            return mismatch
        if any(c in state.current_bottom_2 for c in top_2):
            state.current_bottom_2 = []
        state.current_top_2 = top_2
        logger.info(f"[Q] top_2 q={question_id} top_2={top_2}")
        await send_state_update({
            "type": "top_2_selected",
            "state": "questionnaire",
            "question_id": question_id,
            "top_2": top_2,
        })
        return await _enter_question_step(question_id, flow.after_positive_choices(answer_fmt, state))

    @function_tool()
    async def notify_top_2(question_id: int, top_2: list[str]):
        """Records the choices the user picked as BEST / FAVORITE (as many as asked). Call IMMEDIATELY once identified. / Enregistre les choix « le plus » (préférés / qui représentent le plus). Appeler IMMÉDIATEMENT."""
        return await _notify_top_2_now(question_id, top_2)

    async def _notify_bottom_2_now(question_id: int, bottom_2: list[str]) -> str:
        """Logique commune à l'outil notify_bottom_2 et au clic utilisateur (_handle_bottom_2_clicked)."""
        labels = _choice_labels(question_id)
        bottom_2 = flow.resolve_choices(bottom_2, labels)
        if unknown := flow.unknown_choices(bottom_2, labels):
            logger.warning(f"[Q] bottom_2 refusé, choix inconnu : {bottom_2}")
            return unknown
        overlap = [c for c in bottom_2 if c in state.current_top_2]
        if overlap:
            logger.warning(f"[Q] bottom_2 refusé, déjà choisi en top_2 : {overlap}")
            return (f"[rejected] {overlap} already chosen as {answer_fmt.positive_label}. "
                    "Do not record it. Briefly ask again among the remaining choices only.")
        mismatch = flow.count_mismatch(bottom_2, answer_fmt.negative_count, answer_fmt.negative_label)
        if mismatch:
            logger.warning(f"[Q] bottom_2 refusé : {len(bottom_2)} choix, attendu {answer_fmt.negative_count}")
            return mismatch
        state.current_bottom_2 = bottom_2
        logger.info(f"[Q] bottom_2 q={question_id} bottom_2={bottom_2}")
        await send_state_update({
            "type": "bottom_2_selected",
            "state": "questionnaire",
            "question_id": question_id,
            "bottom_2": bottom_2,
        })
        return await _enter_question_step(question_id, flow.after_negative_choices(answer_fmt, state))

    @function_tool()
    async def notify_bottom_2(question_id: int, bottom_2: list[str]):
        """Records the choices the user picked as LEAST liked / LEAST representative (as many as asked). Call IMMEDIATELY once identified. / Enregistre les choix « le moins ». Appeler IMMÉDIATEMENT."""
        return await _notify_bottom_2_now(question_id, bottom_2)

    @function_tool()
    async def justification_done(question_id: int):
        """Call AFTER the user has explained the choice you just asked about. The next step is chosen automatically. / Appeler APRÈS que l'utilisateur a justifié le choix demandé ; l'étape suivante est choisie automatiquement."""
        if state.phase not in (AgentPhase.Q_JUSTIFY_POSITIVE, AgentPhase.Q_JUSTIFY_NEGATIVE):
            logger.warning(f"[Q] justification_done hors justification (state={state.phase.name}) — ignoré")
            return t("continue_naturally", lang)
        logger.info(f"[Q] justification_done q={question_id} phase={state.phase.name} index={state.justify_index}")
        return await _enter_question_step(question_id, flow.after_justification(answer_fmt, state))

    @function_tool()
    async def notify_asking_top_2(question_id: int):
        """Call ONCE, RIGHT BEFORE asking the user for their 2 favorite choices. / Appeler UNE SEULE FOIS, JUSTE AVANT de demander les 2 choix préférés."""
        logger.info(f"[Q] notify_asking_top_2 q={question_id}")
        await send_state_update({
            "type": "step_asking_top_2",
            "state": "questionnaire",
            "question_id": question_id,
        })
        return t("frontend_notified_top_2", lang)

    @function_tool()
    async def notify_asking_intensity():
        """Call ONCE, RIGHT BEFORE asking the user their fragrance intensity preference. / Appeler UNE SEULE FOIS, JUSTE AVANT de demander la préférence d'intensité."""
        if error := _questionnaire_incomplete_error():
            return error
        logger.info("[STATE] notify_asking_intensity")
        await send_state_update({
            "type": "step_asking_intensity",
            "state": "questionnaire",
        })
        return t("frontend_notified_intensity", lang)

    @function_tool()
    async def notify_asking_perfume_name(formula_type: str):
        """Call ONCE, right after the user answered their intensity preference, INSTEAD of calling generate_formulas directly. formula_type: 'frais', 'mix', or 'puissant'. Shows a text field on screen for the user to type their perfume's name — do NOT expect a spoken answer. / Appeler UNE SEULE FOIS, juste après que l'utilisateur ait répondu sur sa préférence d'intensité, À LA PLACE d'appeler generate_formulas directement. formula_type : 'frais', 'mix' ou 'puissant'. Affiche un champ de texte à l'écran pour que l'utilisateur tape le nom de son parfum — n'attendez pas de réponse orale."""
        if error := _questionnaire_incomplete_error():
            return error
        state.formula_type = formula_type
        logger.info(f"[STATE] notify_asking_perfume_name type={formula_type}")
        await send_state_update({
            "type": "step_asking_perfume_name",
            "state": "questionnaire",
        })
        next_prompt = await advance_to(AgentPhase.PERFUME_NAME)
        return next_prompt

    @function_tool()
    async def save_answer(question_id: int, question_text: str, top_2: list[str], bottom_2: list[str]):
        """Saves the user's confirmed choices for a question. Call ONLY after explicit user confirmation. / Sauvegarde les choix confirmés pour une question. Appeler UNIQUEMENT après confirmation explicite."""
        if state.phase != AgentPhase.Q_CONFIRM:
            logger.warning(f"[Q] save_answer appelé en dehors de Q_CONFIRM (state={state.phase.name}) — ignoré")
            return t("cannot_save_answer", lang)

        # Source de vérité : les choix enregistrés via notify_top_2/notify_bottom_2, que l'écran
        # affiche. Si le LLM passe d'autres valeurs (changement d'avis au récap non notifié),
        # on refuse : sinon la base et les cartes à l'écran divergent.
        if (flow.resolve_choices(top_2, _choice_labels(question_id)) != state.current_top_2
                or flow.resolve_choices(bottom_2, _choice_labels(question_id)) != state.current_bottom_2):
            logger.warning(f"[Q] save_answer refusé : args {top_2}/{bottom_2} ≠ état {state.current_top_2}/{state.current_bottom_2}")
            return ("[rejected] These choices differ from the recorded ones "
                    f"({state.current_top_2} / {state.current_bottom_2}). If the user changed their mind, call "
                    "notify_top_2 or notify_bottom_2 with the new complete selection first (the flow will continue "
                    "from there); otherwise call save_answer again with the recorded choices.")
        top_2, bottom_2 = state.current_top_2, state.current_bottom_2

        resp = await http.post(
            f"/api/session/{session_id}/save-answer",
            json={
                "question_id": question_id,
                "question_text": question_text,
                "top_2": top_2,
                "bottom_2": bottom_2,
            },
        )
        if resp.status_code != 200:
            detail = resp.json().get("detail", t("error", lang))
            return err(detail, lang)

        state.answers_saved += 1
        state.current_top_2 = []
        state.current_bottom_2 = []
        logger.info(f"[Q] Answer saved q={question_id} ({state.answers_saved}/{len(config['questions'])})")

        await send_state_update({
            "type": "answer_saved",
            "state": "questionnaire",
            "question_id": question_id,
            "top_2": top_2,
            "bottom_2": bottom_2,
        })

        # Avancer à la question suivante ou à la phase intensité
        num_questions = len(config["questions"])
        if state.current_question_index + 1 < num_questions:
            state.current_question_index += 1
            return await advance_to(AgentPhase.Q_FAVORITES)
        else:
            return await advance_to(AgentPhase.INTENSITY)

    def _questionnaire_incomplete_error() -> str | None:
        """Garde-fou anti-hallucination : le LLM peut être tenté d'appeler generate_formulas
        prématurément si l'utilisateur dit quelque chose comme "vous me conseillez quoi ?" en
        plein questionnaire. Le prompt seul ne suffit pas à empêcher ça de façon fiable — ce
        contrôle est fait ici, en dur, en plus des instructions du prompt. Retourne un message
        d'erreur si le questionnaire n'est pas terminé, sinon None."""
        num_questions = len(config.get("questions", []))
        if state.answers_saved < num_questions:
            logger.warning(
                f"[GUARD] generate_formulas/generate_catalog_matches appelé prématurément "
                f"— answers_saved={state.answers_saved}/{num_questions} phase={state.phase.name}"
            )
            return t("questionnaire_incomplete", lang, answered=state.answers_saved, total=num_questions)
        return None

    async def _generate_formulas_now(formula_type: str) -> str:
        """Logique commune à l'outil generate_formulas et à la reprise automatique après
        saisie du nom du parfum (_handle_perfume_name_submitted) — appelle le backend, notifie
        le frontend, avance la phase."""
        state.formula_type = formula_type
        logger.info(f"[FORMULAS] generate_formulas type={formula_type}")
        await send_state_update({"type": "state_change", "state": "generating_formulas"})
        resp = await http.post(
            f"/api/session/{session_id}/generate-formulas",
            json={"formula_type": formula_type},
        )
        if resp.status_code != 200:
            detail = resp.json().get("detail", t("unable_to_generate_formulas", lang))
            logger.error(f"[FORMULAS] génération échouée ({resp.status_code}) : {detail}")
            # Sinon le front reste indéfiniment sur l'écran de génération
            await send_state_update({"type": "state_change", "state": "questionnaire"})
            return err(detail, lang)
        data = resp.json()
        await send_state_update({
            "type": "formulas_generated",
            "state": "completed",
            "formulas": data["formulas"],
        })
        next_prompt = await advance_to(AgentPhase.PRESENT_FORMULAS)
        return json.dumps(data, ensure_ascii=False) + "\n\n" + next_prompt

    @function_tool()
    async def generate_formulas(formula_type: str):
        """Generates 2 personalized perfume formulas. formula_type: 'frais', 'mix', or 'puissant'. / Génère 2 formules de parfum personnalisées. formula_type : 'frais', 'mix' ou 'puissant'."""
        if error := _questionnaire_incomplete_error():
            return error
        return await _generate_formulas_now(formula_type)

    @function_tool()
    async def generate_catalog_matches():
        """Selects 2-3 real perfumes from the catalog matching the user's preferences. / Sélectionne 2-3 parfums réels du catalogue correspondant aux préférences de l'utilisateur."""
        if error := _questionnaire_incomplete_error():
            return error
        logger.info("[CATALOG] generate_catalog_matches")
        await send_state_update({"type": "state_change", "state": "generating_formulas"})
        resp = await http.post(f"/api/session/{session_id}/generate-formulas", json={})
        if resp.status_code != 200:
            detail = resp.json().get("detail", t("unable_to_find_matches", lang))
            return err(detail, lang)
        data = resp.json()
        await send_state_update({
            "type": "formulas_generated",
            "state": "completed",
            "formulas": data["formulas"],
        })
        next_prompt = await advance_to(AgentPhase.PRESENT_FORMULAS)
        return json.dumps(data, ensure_ascii=False) + "\n\n" + next_prompt

    @function_tool()
    async def select_formula(formula_index: int):
        """Saves the user's chosen formula/perfume by its index (0-based: 0, 1, or 2 if a third option exists). / Sauvegarde la formule ou le parfum choisi par son index (0-based : 0, 1, ou 2 si une troisième option existe)."""
        state.selected_formula_index = formula_index
        logger.info(f"[FORMULAS] select_formula index={formula_index}")
        resp = await http.post(
            f"/api/session/{session_id}/select-formula",
            json={"formula_index": formula_index},
        )
        if resp.status_code != 200:
            detail = resp.json().get("detail", t("error", lang))
            return err(detail, lang)
        data = resp.json()
        await send_state_update({
            "type": "formula_selected",
            "state": "customization",
            "formula_index": formula_index,
            "formula": data["formula"],
            "reference": data.get("reference"),
        })
        return await advance_to(AgentPhase.CUSTOMIZATION)

    @function_tool()
    async def get_available_ingredients(note_type: str):
        """Returns available ingredients for a note type (top, heart, base), filtered by user allergies. Call BEFORE suggesting replacements. / Retourne les ingrédients disponibles filtrés par allergies. Appeler AVANT de proposer des remplacements."""
        resp = await http.get(f"/api/session/{session_id}/available-ingredients/{note_type}")
        if resp.status_code != 200:
            detail = resp.json().get("detail", t("error", lang))
            return err(detail, lang)
        return json.dumps(resp.json(), ensure_ascii=False)

    @function_tool()
    async def replace_note(note_type: str, old_note: str, new_note: str):
        """Replaces a note in the selected formula. note_type: 'top', 'heart', or 'base'. Call ONLY after user confirms the replacement. / Remplace une note dans la formule. Appeler UNIQUEMENT après confirmation de l'utilisateur."""
        logger.info(f"[FORMULAS] replace_note {note_type} {old_note} → {new_note}")
        resp = await http.post(
            f"/api/session/{session_id}/replace-note",
            json={"note_type": note_type, "old_note": old_note, "new_note": new_note},
        )
        if resp.status_code != 200:
            detail = resp.json().get("detail", t("error", lang))
            return err(detail, lang)
        data = resp.json()
        await send_state_update({
            "type": "formula_updated",
            "state": "customization",
            "formula": data["formula"],
        })
        return t("note_replaced", lang, old_note=old_note, new_note=new_note)

    @function_tool()
    async def change_formula_type(formula_type: str):
        """Changes the type (frais/mix/puissant) of the already selected formula. Use ONLY in customization phase (after a formula has been selected). / Change le type de la formule déjà sélectionnée. À utiliser UNIQUEMENT en phase de personnalisation."""
        logger.info(f"[FORMULAS] change_formula_type → {formula_type}")
        resp = await http.post(
            f"/api/session/{session_id}/change-formula-type",
            json={"formula_type": formula_type},
        )
        if resp.status_code != 200:
            detail = resp.json().get("detail", t("error", lang))
            return err(detail, lang)
        data = resp.json()
        await send_state_update({
            "type": "formula_selected",
            "state": "customization",
            "formula": data["formula"],
        })
        return t("formula_type_changed", lang, formula_type=formula_type)

    @function_tool()
    async def enter_pause_mode():
        """Puts the assistant in standby mode. Call IMMEDIATELY after the goodbye message. / Met l'assistante en veille. Appeler IMMÉDIATEMENT après le message d'au revoir."""
        paused[0] = True
        session.input.set_audio_enabled(False)
        state.phase = AgentPhase.STANDBY
        logger.info("[STATE] → STANDBY")
        await send_state_update({"type": "state_change", "state": "standby"})
        return t("standby_activated", lang)

    # ─── Accompagnement physique (capacité guide_destination du client) ────
    # Le backend ne pilote pas le robot : il demande au client de partir (robot_navigate),
    # puis attend robot_arrived / robot_failed sur le data channel (voir _on_data_received).

    async def _start_guiding(notify_client: bool):
        state.guide_status = "moving"
        state.guide_error = None
        _cancel_inactivity_shutdown("Accompagnement en cours")
        # Pas d'écoute pendant le trajet : bruit des moteurs et passants déclencheraient l'agent.
        session.input.set_audio_enabled(False)
        if notify_client:
            await send_state_update({"type": "robot_navigate", "destination": guide_dest})
        logger.info(f"[GUIDE] Départ vers {guide_dest!r} (demandé par {'agent' if notify_client else 'client'})")

    @function_tool()
    async def guide_visitor():
        """Physically accompanies the user to the destination. Call ONLY right after the user accepted to be accompanied. / Accompagne physiquement l'utilisateur jusqu'au lieu. Appeler UNIQUEMENT juste après que l'utilisateur a accepté d'être accompagné."""
        if not guide_dest or state.guide_status is not None:
            return "[guide unavailable or already done]"
        await _start_guiding(notify_client=True)
        return await advance_to(AgentPhase.GUIDING)

    async def _handle_guide_event(kind: str, message: str | None = None):
        """robot_navigation_started (clic manuel sur le client), robot_arrived, robot_failed."""
        if kind == "started":
            # Le visiteur a lancé le trajet lui-même : l'agent l'annonce au lieu de le proposer.
            if paused[0] or state.guide_status is not None or state.phase not in (AgentPhase.CUSTOMIZATION, AgentPhase.STANDBY):
                logger.info(f"[GUIDE] Départ manuel ignoré — phase={state.phase.name} paused={paused[0]}")
                return
            try:
                session.interrupt(force=True)
            except Exception:
                pass
            await _start_guiding(notify_client=False)
        else:
            if state.phase != AgentPhase.GUIDING or state.guide_status != "moving":
                logger.info(f"[GUIDE] {kind} ignoré — phase={state.phase.name} status={state.guide_status}")
                return
            state.guide_status = "arrived" if kind == "arrived" else "failed"
            state.guide_error = (message or "")[:200] or None
            logger.info(f"[GUIDE] {state.guide_status} — {state.guide_error or ''}")
        await advance_to(AgentPhase.GUIDING)
        try:
            await session.generate_reply()
        except Exception as e:
            logger.warning(f"[GUIDE] Échec réplique ({kind}): {e}")

    # ─── Collecte des tools ────────────────────────────────────────────────
    # Les choix top_2/bottom_2 sont désormais cliquables dans toute session vocale — pas
    # seulement en input_mode="click" — via notify_asking_top_2/notify_asking_bottom_2
    # (toujours appelés) et _handle_top_2_clicked/_handle_bottom_2_clicked côté data channel
    # 'control' (voir _on_data_received). Plus besoin de tools dédiés au mode clic.

    all_tools = [
        save_user_profile,
        notify_top_2,
        notify_bottom_2,
        justification_done,
        notify_asking_top_2,
        notify_asking_intensity,
        save_answer,
        select_formula,
        enter_pause_mode,
    ]
    if guide_dest:
        all_tools.append(guide_visitor)
    if brand_profile.result_engine == "catalog":
        all_tools.append(generate_catalog_matches)
    else:
        all_tools += [notify_asking_perfume_name, generate_formulas, get_available_ingredients, replace_note, change_formula_type]

    # ─── Création de l'AgentSession ────────────────────────────────────────

    logger.info(f"[AGENT_SESSION] Création AgentSession — STT=nova-3 LLM=gpt-4.1-mini TTS=sonic-3 voice={config.get('voice_id')} lang={config.get('language', 'fr')}")
    initial_prompt = get_prompt(state, config, ai_name, lang, input_mode)
    agent = StatefulAgent(instructions=initial_prompt, tools=all_tools)
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language=config.get("language", "fr"),
        ),
        llm=openai.LLM(model="gpt-4.1-mini"),
        tts=cartesia.TTS(
            api_key=settings.cartesia_api_key,
            model="sonic-3",
            voice=config["voice_id"],
            language=config.get("language", "fr"),
        ),
        vad=ctx.proc.userdata["vad"],
        # Endpointing dynamique : au lieu d'un délai fixe unique pour tout le monde,
        # le SDK apprend en direct le rythme de pause propre à chaque utilisateur
        # (moyenne mobile exponentielle sur ses pauses naturelles) et ajuste le délai
        # d'attente en conséquence — quelqu'un qui hésite garde un délai plus long
        # appris automatiquement, quelqu'un qui parle sans pause obtient une réponse
        # plus rapide. max_delay reste un plafond de sécurité fixe, jamais dépassé.
        # Remplace l'ancien `allow_interruptions=False` (déprécié) — `interruption:
        # {"enabled": False}` reproduit exactement le même comportement.
        turn_handling={
            "endpointing": {"mode": "dynamic", "min_delay": 0.5, "max_delay": 3.0},
            "interruption": {"enabled": False},
        },
    )
    logger.info("[AGENT_SESSION] ✅ AgentSession créée")

    # ─── Avatar Bey ────────────────────────────────────────────────────────

    if use_avatar[0]:
        try:
            avatar_id = pick_avatar(voice_gender)
            logger.info(f"[AVATAR] Démarrage avatar Bey — avatar_id={avatar_id} gender={voice_gender}")
            avatar = bey.AvatarSession(avatar_id=avatar_id)
            await asyncio.wait_for(avatar.start(session, room=ctx.room), timeout=15.0)
            logger.info("[AVATAR] ✅ Avatar Bey démarré")
        except asyncio.TimeoutError:
            logger.error("[AVATAR] ❌ Timeout (15s) démarrage avatar Bey — on continue sans avatar")
            use_avatar[0] = False
            asyncio.ensure_future(send_state_update({"type": "avatar_disabled", "reason": "timeout"}))
        except Exception as e:
            logger.error(f"[AVATAR] ❌ Erreur démarrage avatar Bey ({type(e).__name__}: {e}) — on continue sans avatar")
            use_avatar[0] = False
            asyncio.ensure_future(send_state_update({"type": "avatar_disabled", "reason": "error"}))

        if use_avatar[0]:
            import time as _time
            _BEY_IDENTITY = "bey-avatar-agent"
            bey_stable_count = 0
            logger.info(f"[BEY_WAIT] Attente stabilité Bey at {_time.time():.3f}")
            for _i in range(50):
                bey_participant = next(
                    (p for p in ctx.room.remote_participants.values()
                     if p.identity == _BEY_IDENTITY),
                    None,
                )
                if bey_participant and any(
                    pub.kind == rtc.TrackKind.KIND_VIDEO
                    for pub in bey_participant.track_publications.values()
                ):
                    bey_stable_count += 1
                    logger.debug(f"[BEY_WAIT] stable_count={bey_stable_count}/3 at {_time.time():.3f}")
                    if bey_stable_count >= 3:
                        logger.info(f"[BEY_WAIT] ✅ Bey stable at {_time.time():.3f}")
                        break
                else:
                    if bey_stable_count > 0:
                        logger.warning(f"[BEY_WAIT] Bey lost track, reset stable_count at {_time.time():.3f}")
                    bey_stable_count = 0
                await asyncio.sleep(0.5)
            else:
                logger.warning(f"[BEY_WAIT] Bey pas prêt après 25s, on continue quand même at {_time.time():.3f}")

            logger.info(f"[SESSION] Attente 1.5s Cartesia + Bey DataStream at {_time.time():.3f}")
            await asyncio.sleep(1.5)
            logger.info(f"[SESSION] Attente terminée at {_time.time():.3f}")

    # ─── Démarrage de la session ───────────────────────────────────────────

    import time as _time
    logger.info(f"[SESSION] Appel session.start() at {_time.time():.3f}")
    try:
        await session.start(room=ctx.room, agent=agent)
        logger.info(f"[SESSION] ✅ session.start() terminé at {_time.time():.3f}")
    except Exception as e:
        logger.exception(f"[SESSION] ❌ Erreur session.start(): {e}")
        await http.aclose()
        return

    # ─── Event listeners ──────────────────────────────────────────────────

    # ─── Coupure automatique en cas d'inactivité prolongée ─────────────────
    # Objectif : éviter de gaspiller le quota Beyond Presence (avatar vidéo),
    # Cartesia et Deepgram si l'utilisateur laisse la session ouverte sans plus
    # interagir (parti sans se déconnecter, onglet oublié en arrière-plan, etc.).
    # `user_state_changed` passe à "away" après 15s de silence complet (utilisateur
    # ET agent) — c'est le comportement par défaut du SDK (user_away_timeout=15.0,
    # déjà actif, on ne fait qu'en écouter l'événement). On laisse ensuite un délai
    # supplémentaire avant de couper pour de bon, au cas où l'utilisateur réfléchit
    # simplement longtemps à sa réponse.
    #
    # Le SDK ne base "away" que sur le silence micro de l'utilisateur — il ignore les
    # interactions silencieuses (saisie du nom du parfum au clavier, clic sur les cartes de
    # choix) ainsi que l'agent qui continue de parler pendant ce temps (ex: présentation des
    # formules juste après une saisie clavier). Sans le garde-fou ci-dessous, le timer armé
    # avant une saisie clavier continuait de courir et coupait la session en plein milieu
    # d'une réplique de l'agent. On annule donc aussi le timer dès que l'agent se met à parler.
    _AWAY_GRACE_PERIOD_SECONDS = 45.0  # + 15s de détection SDK = ~60s au total
    inactivity_shutdown_task: list[asyncio.Task | None] = [None]

    def _cancel_inactivity_shutdown(reason: str):
        if inactivity_shutdown_task[0] is not None and not inactivity_shutdown_task[0].done():
            inactivity_shutdown_task[0].cancel()
            logger.info(f"[INACTIVITY] {reason} — coupure programmée annulée")

    async def _shutdown_after_inactivity():
        try:
            await asyncio.sleep(_AWAY_GRACE_PERIOD_SECONDS)
            logger.warning(f"[INACTIVITY] Session inactive depuis ~{15 + _AWAY_GRACE_PERIOD_SECONDS:.0f}s — fermeture pour room={ctx.room.name}")
            farewell = t("inactivity_farewell", lang)
            try:
                await session.generate_reply(instructions=f"Say EXACTLY this and nothing else: \"{farewell}\"")
            except Exception as e:
                logger.warning(f"[INACTIVITY] Erreur lors du message d'au revoir: {e}")
            ctx.shutdown(reason="user inactivity timeout")
        except asyncio.CancelledError:
            pass

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        # Sert à mesurer le délai perçu par l'utilisateur : le temps passé en
        # "thinking" (entre la fin de la question de l'utilisateur et le début de la
        # réponse parlée) couvre le LLM + les éventuels tool calls réseau vers le
        # backend — à comparer aux logs [HTTP_TIMING] pour savoir où part le temps.
        logger.info(f"[AGENT_STATE] {ev.old_state} → {ev.new_state} at {ev.created_at:.3f}")
        if ev.new_state == "speaking":
            _cancel_inactivity_shutdown("Agent en train de parler")
        asyncio.ensure_future(send_state_update({
            "type": "agent_state",
            "state": ev.new_state,
        }))

    @session.on("user_state_changed")
    def on_user_state_changed(ev):
        logger.info(f"[USER_STATE] {ev.old_state} → {ev.new_state} at {ev.created_at:.3f}")
        if ev.new_state == "away":
            # Silence normal pendant l'accompagnement (micro coupé, visiteur qui marche).
            if state.phase == AgentPhase.GUIDING and state.guide_status == "moving":
                return
            if inactivity_shutdown_task[0] is None or inactivity_shutdown_task[0].done():
                inactivity_shutdown_task[0] = asyncio.ensure_future(_shutdown_after_inactivity())
        else:
            _cancel_inactivity_shutdown("Activité détectée")

    async def _handle_perfume_name_submitted(name: str):
        """Reçoit le nom du parfum saisi au clavier par l'utilisateur (data channel 'control',
        voir _on_data_received) — pas de dictée orale pour éviter les fautes d'orthographe.
        Sauvegarde le nom, fait réagir l'agent brièvement, puis enchaîne directement sur
        generate_formulas (le formula_type a déjà été stocké par notify_asking_perfume_name)."""
        state.perfume_name = name
        logger.info(f"[PERFUME_NAME] Reçu: {name!r}")
        try:
            await http.post(
                f"/api/session/{session_id}/save-profile",
                json={"field": "perfume_name", "value": name},
            )
        except Exception as e:
            logger.warning(f"[PERFUME_NAME] Échec sauvegarde profil: {e}")

        ack = t("perfume_name_ack_instruction", lang, name=name)
        try:
            await session.generate_reply(instructions=ack)
        except Exception as e:
            logger.warning(f"[PERFUME_NAME] Échec réplique d'accueil: {e}")

        await _generate_formulas_now(state.formula_type or "mix")
        # _generate_formulas_now (appelé directement, pas via un tool call LLM) fait avancer
        # la phase vers PRESENT_FORMULAS mais ne parle pas de lui-même — contrairement à un
        # vrai tool call où le framework relance automatiquement le LLM après le retour du
        # tool. Il faut donc déclencher explicitement la présentation des formules ici.
        try:
            await session.generate_reply()
        except Exception as e:
            logger.warning(f"[PERFUME_NAME] Échec relance présentation formules: {e}")

    async def _handle_top_2_clicked(question_id: int, values: list[str]):
        """Reçoit les 2 favoris choisis par clic (data channel 'control', voir
        _on_data_received) — alternative au fait de les dire à l'oral, utile quand l'IA ne
        comprend pas bien une réponse vocale. Rejoue exactement la même logique que le tool
        notify_top_2 (que le LLM aurait appelé après avoir compris la réponse orale), puis
        relance une réplique pour que l'agent enchaîne sur l'étape suivante — le prompt système
        a déjà été mis à jour par _notify_top_2_now/advance_to."""
        q = next((qq for qq in config["questions"] if qq["id"] == question_id), None)
        if not q or state.phase != AgentPhase.Q_FAVORITES:
            logger.warning(f"[CLICK] top_2 ignoré — question_id={question_id} phase={state.phase.name}")
            return
        logger.info(f"[CLICK] top_2 reçu q={question_id} values={values}")
        await _notify_top_2_now(question_id, values)
        try:
            await session.generate_reply()
        except Exception as e:
            logger.warning(f"[CLICK] Échec relance après top_2: {e}")

    async def _handle_bottom_2_clicked(question_id: int, values: list[str]):
        """Équivalent de _handle_top_2_clicked pour les 2 moins aimés (phase Q_LEAST)."""
        q = next((qq for qq in config["questions"] if qq["id"] == question_id), None)
        if not q or state.phase != AgentPhase.Q_LEAST:
            logger.warning(f"[CLICK] bottom_2 ignoré — question_id={question_id} phase={state.phase.name}")
            return
        logger.info(f"[CLICK] bottom_2 reçu q={question_id} values={values}")
        await _notify_bottom_2_now(question_id, values)
        try:
            await session.generate_reply()
        except Exception as e:
            logger.warning(f"[CLICK] Échec relance après bottom_2: {e}")

    def _on_data_received(data_packet):
        try:
            msg = json.loads(data_packet.data.decode("utf-8"))
            msg_type = msg.get("type")

            if msg_type == "interrupt":
                user_interrupted[0] = True
                try:
                    session.interrupt(force=True)
                except Exception as e:
                    logger.warning(f"[INTERRUPT] Could not interrupt speech: {e}")
                session.input.set_audio_enabled(False)
                logger.info(f"[INTERRUPT] Agent interrompu pour room={ctx.room.name}")

            elif msg_type == "resume_listen" and user_interrupted[0]:
                user_interrupted[0] = False
                session.input.set_audio_enabled(True)
                logger.info(f"[INTERRUPT] Reprise écoute pour room={ctx.room.name}")

            elif msg_type == "repeat":
                pass  # TODO

            elif msg_type == "resume" and paused[0]:
                paused[0] = False
                state.phase = AgentPhase.STANDBY
                session.input.set_audio_enabled(True)
                logger.info(f"[RESUME] Agent réactivé via bouton pour room={ctx.room.name}")
                resume_prompt = t("resume_instruction", lang)
                asyncio.ensure_future(session.generate_reply(instructions=resume_prompt))

            elif msg_type == "perfume_name_submitted" and state.phase == AgentPhase.PERFUME_NAME:
                name = (msg.get("name") or "").strip()
                if name:
                    asyncio.ensure_future(_handle_perfume_name_submitted(name))

            elif msg_type == "robot_navigation_started" and guide_dest:
                asyncio.ensure_future(_handle_guide_event("started"))

            elif msg_type == "robot_arrived" and guide_dest:
                asyncio.ensure_future(_handle_guide_event("arrived"))

            elif msg_type == "robot_failed" and guide_dest:
                asyncio.ensure_future(_handle_guide_event("failed", msg.get("message")))

            elif msg_type == "questionnaire_top_2":
                question_id = msg.get("question_id")
                values = msg.get("values") or []
                # Nombre attendu = format du questionnaire (1 pour Help, 2 pour Lylo…)
                if question_id is not None and len(values) == answer_fmt.positive_count:
                    asyncio.ensure_future(_handle_top_2_clicked(question_id, values))
                else:
                    logger.warning(f"[CLICK] top_2 ignoré : {len(values)} valeur(s), attendu {answer_fmt.positive_count}")

            elif msg_type == "questionnaire_bottom_2":
                question_id = msg.get("question_id")
                values = msg.get("values") or []
                if question_id is not None and len(values) == answer_fmt.negative_count:
                    asyncio.ensure_future(_handle_bottom_2_clicked(question_id, values))
                else:
                    logger.warning(f"[CLICK] bottom_2 ignoré : {len(values)} valeur(s), attendu {answer_fmt.negative_count}")

        except Exception as e:
            logger.error(f"[DATA_RECEIVED] Erreur traitement message: {e}")

    ctx.room.on("data_received", _on_data_received)

    def _on_participant_disconnected(participant):
        if participant.identity == "bey-avatar-agent" and use_avatar[0]:
            use_avatar[0] = False
            logger.warning(f"[AVATAR] Bey déconnecté, passage en mode audio-only pour room={ctx.room.name}")
            asyncio.ensure_future(send_state_update({"type": "avatar_disabled"}))

    ctx.room.on("participant_disconnected", _on_participant_disconnected)

    # ─── Démarrage : accueil ──────────────────────────────────────────────

    logger.info(f"[GREETING] Appel generate_reply() — phase={state.phase.name} at {_time.time():.3f}")
    try:
        await session.generate_reply(instructions=initial_prompt)
        logger.info(f"[GREETING] ✅ generate_reply() terminé at {_time.time():.3f}")
    except Exception as e:
        logger.exception(f"[GREETING] ❌ Erreur generate_reply(): {e}")

    async def _on_shutdown():
        await http.aclose()
        logger.info(f"[SHUTDOWN] Session terminée pour room={ctx.room.name}")

    ctx.add_shutdown_callback(_on_shutdown)
    logger.info(f"[ENTRYPOINT] ✅ Agent actif — room={ctx.room.name} phase={state.phase.name}")


# ─────────────────────────────────────────────
# Prewarm & Worker
# ─────────────────────────────────────────────

def prewarm(proc: JobProcess):
    logger.info(f"[PREWARM] Démarrage prewarm — PID={os.getpid()}")
    try:
        # min_silence_duration=1.5 (avant) forçait TOUJOURS 1.5s de silence avant même
        # de considérer le tour terminé, quel que soit le rythme de l'utilisateur — la
        # principale source du délai de 2-3s observé en usage réel (voir PERF_TODO.md).
        # 0.6s se rapproche du défaut recommandé par le plugin Silero (0.55s, cf. doc
        # livekit.plugins.silero.vad) : le VAD n'a plus besoin de porter seul la
        # protection contre les hésitations — c'est le rôle de l'endpointing dynamique
        # configuré sur l'AgentSession (turn_handling), qui apprend le rythme de pause
        # propre à chaque utilisateur et garde max_delay comme filet de sécurité.
        proc.userdata["vad"] = silero.VAD.load(
            min_speech_duration=0.3,
            min_silence_duration=0.6,
        )
        logger.info("[PREWARM] ✅ Silero VAD chargé")
    except Exception as e:
        logger.exception(f"[PREWARM] ❌ ERREUR chargement Silero VAD: {e}")
        raise


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            # Configurable via LIVEKIT_AGENT_NAME (.env) — mettre "lylo-dev" en local
            # pour éviter que LiveKit Cloud (partagé avec la prod) ne dispatche une
            # session locale vers l'agent Railway ou inversement (voir config.py).
            agent_name=settings.livekit_agent_name,
            num_idle_processes=3,
            load_threshold=0.9,
        )
    )
