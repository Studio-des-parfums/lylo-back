"""Accompagnement physique du visiteur en fin de parcours (capacité « guide_destination »).

Le client (ex. tablette d'un robot) annonce au démarrage de session qu'il peut accompagner le
visiteur jusqu'à un lieu (`guide_destination`). Le backend ne sait rien du robot lui-même :
il propose l'accompagnement, puis attend que le client signale l'arrivée (ou l'échec).

- `offer_addendum` : ajouté à la mission CUSTOMIZATION tant que l'accompagnement n'a pas eu
  lieu — remplace l'au revoir final par la proposition d'accompagnement.
- `guiding` : mission de la phase GUIDING (en route / arrivé / échec).
"""
from app.agent.prompts.context import PromptContext
from app.agent.state import AgentPhase


def guide_destination(config: dict) -> str | None:
    """Lieu annoncé par le client, ou None si la capacité n'est pas disponible."""
    value = (config.get("guide_destination") or "").strip()
    return value[:100] or None


_OFFER = {
    "fr": """

--- ACCOMPAGNEMENT (prioritaire sur la consigne de fin ci-dessus) ---
Vous pouvez accompagner physiquement {first_name} jusqu'à {dest}. Quand la personnalisation est terminée et qu'il/elle n'a plus de questions, NE dites PAS au revoir : proposez en UNE phrase : « Voulez-vous que je vous accompagne jusqu'à {dest} ? »
— Si oui : appelez IMMÉDIATEMENT guide_visitor(), sans rien dire avant.
— Si non : UNE courte phrase d'au revoir, puis appelez IMMÉDIATEMENT enter_pause_mode().
Ne proposez l'accompagnement qu'UNE seule fois.""",
    "en": """

--- ACCOMPANYING THE USER (takes priority over the closing instruction above) ---
You can physically accompany {first_name} to {dest}. Once customization is done and they have no more questions, do NOT say goodbye: offer in ONE sentence: "Would you like me to take you to {dest}?"
— If yes: IMMEDIATELY call guide_visitor(), without saying anything first.
— If no: ONE short farewell sentence, then IMMEDIATELY call enter_pause_mode().
Offer this only ONCE.""",
    "es": """

--- ACOMPAÑAMIENTO (prioritario sobre la instrucción de cierre anterior) ---
Puede acompañar físicamente a {first_name} hasta {dest}. Cuando la personalización haya terminado y no tenga más preguntas, NO se despida: proponga en UNA frase: «¿Quiere que le acompañe hasta {dest}?»
— Si sí: llame INMEDIATAMENTE a guide_visitor(), sin decir nada antes.
— Si no: UNA breve frase de despedida y luego llame INMEDIATAMENTE a enter_pause_mode().
Proponga el acompañamiento UNA sola vez.""",
    "de": """

--- BEGLEITUNG (hat Vorrang vor der obigen Abschlussanweisung) ---
Du kannst {first_name} persönlich bis zu {dest} begleiten. Wenn die Anpassung abgeschlossen ist und keine Fragen mehr offen sind, verabschiede dich NICHT: biete in EINEM Satz an: „Möchten Sie, dass ich Sie zu {dest} begleite?"
— Bei Ja: rufe SOFORT guide_visitor() auf, ohne vorher etwas zu sagen.
— Bei Nein: EIN kurzer Abschiedssatz, dann rufe SOFORT enter_pause_mode() auf.
Biete die Begleitung nur EINMAL an.""",
    "ar": """

--- المرافقة (لها الأولوية على تعليمات الختام أعلاه) ---
يمكنك مرافقة {first_name} فعليًا حتى {dest}. عندما ينتهي التخصيص ولا تبقى لديه أسئلة، لا تودّعه: اعرض في جملة واحدة: «هل تريد أن أرافقك إلى {dest}؟»
— إذا وافق: استدعِ فورًا guide_visitor() دون أن تقول شيئًا قبل ذلك.
— إذا رفض: جملة وداع قصيرة واحدة، ثم استدعِ فورًا enter_pause_mode().
اعرض المرافقة مرة واحدة فقط.""",
    "ru": """

--- СОПРОВОЖДЕНИЕ (приоритетнее инструкции о завершении выше) ---
Ты можешь лично проводить {first_name} до {dest}. Когда персонализация закончена и вопросов больше нет, НЕ прощайся: предложи ОДНОЙ фразой: «Хотите, я провожу вас до {dest}?»
— Если да: СРАЗУ вызови guide_visitor(), ничего не говоря перед этим.
— Если нет: ОДНА короткая прощальная фраза, затем СРАЗУ вызови enter_pause_mode().
Предлагай сопровождение только ОДИН раз.""",
}

_MOVING = {
    "fr": "Vous accompagnez maintenant {first_name} jusqu'à {dest}. Dites UNE seule phrase courte, par exemple : « Je vous emmène jusqu'à {dest}, suivez-moi ! », puis taisez-vous. N'appelez aucune fonction. Vous serez prévenu(e) automatiquement à l'arrivée.",
    "en": "You are now accompanying {first_name} to {dest}. Say ONE short sentence, e.g. \"I'll take you to {dest}, follow me!\", then stay silent. Do not call any function. You will be notified automatically on arrival.",
    "es": "Ahora acompaña a {first_name} hasta {dest}. Diga UNA sola frase corta, por ejemplo: «Le llevo hasta {dest}, ¡sígame!», y luego guarde silencio. No llame a ninguna función. Se le avisará automáticamente a la llegada.",
    "de": "Du begleitest {first_name} jetzt zu {dest}. Sage EINEN kurzen Satz, z. B. „Ich bringe Sie zu {dest}, folgen Sie mir!\", und schweige dann. Rufe keine Funktion auf. Du wirst bei der Ankunft automatisch benachrichtigt.",
    "ar": "أنت الآن ترافق {first_name} إلى {dest}. قل جملة قصيرة واحدة، مثل: «سأرافقك إلى {dest}، اتبعني!»، ثم التزم الصمت. لا تستدعِ أي دالة. سيتم إبلاغك تلقائيًا عند الوصول.",
    "ru": "Ты сейчас провожаешь {first_name} до {dest}. Скажи ОДНУ короткую фразу, например: «Я провожу вас до {dest}, следуйте за мной!», затем молчи. Не вызывай никаких функций. О прибытии тебе сообщат автоматически.",
}

_ARRIVED = {
    "fr": "Vous êtes arrivés à {dest}. Dites en une ou deux phrases courtes : « Nous y voilà ! Quand vous le souhaitez, cliquez sur le bouton {finish}. Merci et excellente journée ! », puis appelez IMMÉDIATEMENT enter_pause_mode().",
    "en": "You have arrived at {dest}. Say in one or two short sentences: \"Here we are! Whenever you like, tap the {finish} button. Thank you and have a wonderful day!\", then IMMEDIATELY call enter_pause_mode().",
    "es": "Han llegado a {dest}. Diga en una o dos frases cortas: «¡Ya hemos llegado! Cuando lo desee, pulse el botón {finish}. ¡Gracias y que tenga un excelente día!», y luego llame INMEDIATAMENTE a enter_pause_mode().",
    "de": "Ihr seid bei {dest} angekommen. Sage in ein oder zwei kurzen Sätzen: „Da sind wir! Tippen Sie, wann Sie möchten, auf die Schaltfläche {finish}. Vielen Dank und einen wunderschönen Tag!\", dann rufe SOFORT enter_pause_mode() auf.",
    "ar": "لقد وصلتما إلى {dest}. قل في جملة أو جملتين قصيرتين: «ها قد وصلنا! متى شئت، اضغط على زر {finish}. شكرًا لك ويومًا سعيدًا!»، ثم استدعِ فورًا enter_pause_mode().",
    "ru": "Вы прибыли в {dest}. Скажи одной-двумя короткими фразами: «Вот мы и на месте! Когда захотите, нажмите кнопку «{finish}». Спасибо и отличного дня!», затем СРАЗУ вызови enter_pause_mode().",
}

_FAILED = {
    "fr": "Vous n'avez pas pu vous rendre à {dest} (raison technique : {error}). En UNE ou DEUX phrases : excusez-vous simplement, sans détail technique, indiquez qu'un membre de l'équipe peut l'y conduire, remerciez et souhaitez une excellente journée, puis appelez IMMÉDIATEMENT enter_pause_mode().",
    "en": "You could not get to {dest} (technical reason: {error}). In ONE or TWO sentences: simply apologize, without technical details, say a team member can take them there, thank them and wish them a wonderful day, then IMMEDIATELY call enter_pause_mode().",
    "es": "No ha podido llegar a {dest} (motivo técnico: {error}). En UNA o DOS frases: discúlpese sin detalles técnicos, indique que un miembro del equipo puede acompañarle, dé las gracias y desee un excelente día; luego llame INMEDIATAMENTE a enter_pause_mode().",
    "de": "Du konntest {dest} nicht erreichen (technischer Grund: {error}). In EINEM oder ZWEI Sätzen: entschuldige dich ohne technische Details, sage, dass ein Teammitglied die Person hinbringen kann, bedanke dich und wünsche einen schönen Tag, dann rufe SOFORT enter_pause_mode() auf.",
    "ar": "لم تتمكن من الوصول إلى {dest} (سبب تقني: {error}). في جملة أو جملتين: اعتذر ببساطة دون تفاصيل تقنية، وأخبره أن أحد أعضاء الفريق يمكنه مرافقته، واشكره وتمنَّ له يومًا سعيدًا، ثم استدعِ فورًا enter_pause_mode().",
    "ru": "Ты не смог добраться до {dest} (техническая причина: {error}). ОДНОЙ-ДВУМЯ фразами: просто извинись без технических подробностей, скажи, что сотрудник может проводить туда, поблагодари и пожелай отличного дня, затем СРАЗУ вызови enter_pause_mode().",
}

# Libellé du bouton de fin côté client (mêmes textes que l'app tablette).
_FINISH_LABEL = {"fr": "Terminer", "en": "Finish", "es": "Terminar", "de": "Beenden", "ar": "إنهاء", "ru": "Завершить"}


# Le lieu est un nom de salle (« la salle de création »), envoyé au nominatif : l'IA doit
# l'accorder (article, préposition, déclinaison) au lieu de le recopier mot pour mot.
_GRAMMAR_NOTE = {
    "fr": "\n(« {dest} » est le nom du lieu : intégrez-le naturellement à vos phrases, avec la bonne préposition et le bon article.)",
    "en": "\n(\"{dest}\" is the name of the place: weave it naturally into your sentences with the right preposition and article.)",
    "es": "\n(«{dest}» es el nombre del lugar: intégrelo con naturalidad en sus frases, con la preposición y el artículo correctos.)",
    "de": "\n(„{dest}\" ist der Name des Ortes: baue ihn grammatisch korrekt in deine Sätze ein — Präposition, Artikel, Fall.)",
    "ar": "\n(«{dest}» هو اسم المكان: أدرجه بشكل طبيعي في جملك مع حرف الجر والتعريف الصحيحين.)",
    "ru": "\n(«{dest}» — название места: естественно встраивай его в свои фразы, с правильным предлогом и падежом.)",
}


def _fmt(table: dict, ctx: PromptContext, **extra) -> str:
    template = table.get(ctx.lang, table["fr"]) + _GRAMMAR_NOTE.get(ctx.lang, _GRAMMAR_NOTE["fr"])
    return template.format(
        first_name=ctx.state.profile.get("first_name", ""),
        dest=guide_destination(ctx.config) or "",
        finish=_FINISH_LABEL.get(ctx.lang, _FINISH_LABEL["fr"]),
        **extra,
    )


def offer_addendum(ctx: PromptContext) -> str:
    """Proposition d'accompagnement à ajouter à CUSTOMIZATION ("" si non applicable)."""
    if not guide_destination(ctx.config) or ctx.state.guide_status is not None:
        return ""
    return _fmt(_OFFER, ctx)


def guiding(ctx: PromptContext) -> str:
    status = ctx.state.guide_status
    if status == "arrived":
        return _fmt(_ARRIVED, ctx)
    if status == "failed":
        return _fmt(_FAILED, ctx, error=ctx.state.guide_error or "?")
    return _fmt(_MOVING, ctx)


MISSIONS = {
    AgentPhase.GUIDING: guiding,
}
