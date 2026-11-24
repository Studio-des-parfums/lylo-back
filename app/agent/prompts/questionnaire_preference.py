"""Phase 2 — questionnaire au format « préférences » (2 favoris + 2 moins aimés, justifiés).

Textes déplacés tels quels depuis agent.py (get_prompt) — vérifiés par scripts/prompt_snapshot.py.
"""
from app.agent.prompts.context import PromptContext
from app.agent.state import AgentPhase


def q_favorites(ctx: PromptContext) -> str:
    lang, is_en, state, questions, num_questions = ctx.lang, ctx.is_en, ctx.state, ctx.questions, ctx.num_questions
    q = questions[state.current_question_index]
    q_num = state.current_question_index + 1
    choices_str = ", ".join(c["label"] if isinstance(c, dict) else c for c in q.get("choices", []))
    first_name = state.profile.get("first_name", "")

    if is_en:
        mission = f"""It is now question {q_num} of {num_questions}.

Question (id={q['id']}): "{q['question']}"
Available choices: {choices_str}

FIRST action (before speaking): call notify_asking_top_2(question_id={q['id']}) to signal the interface that the cards are now clickable.

STEP: Then, in ONE natural sentence, ask {first_name} for their 2 FAVORITE choices. Do NOT enumerate the choices aloud — the user can see them on screen. The user may answer by speaking OR by clicking the cards on screen — if they click, you will be notified automatically and should NOT call notify_top_2 yourself in that case.

Once the user gives 2 choices ORALLY (if they click instead, skip this — you'll be notified):
1. Match each spoken answer to the closest canonical label from: [{choices_str}]. Use semantic and phonetic understanding — the user may mispronounce, abbreviate, or give a partial answer (e.g. "delhi" → "Delhi", "jazz" → "Jazz et new age", "rock" → "Rock"). NEVER ask for clarification for ambiguous answers — pick the closest match and move on silently.
2. Call notify_top_2(question_id={q['id']}, top_2=[choice1, choice2]) IMMEDIATELY.
3. Your mission for this step is complete."""
    elif lang == "es":
        mission = f"""Esta es ahora la pregunta {q_num} de {num_questions}.

Pregunta (id={q['id']}): "{q['question']}"
Opciones disponibles: {choices_str}

PRIMERA acción (antes de hablar): llame a notify_asking_top_2(question_id={q['id']}) para indicar a la interfaz que las tarjetas ya son clicables.

PASO: Luego, en UNA sola frase natural, pregunte a {first_name} sus 2 opciones FAVORITAS. NO enumere las opciones en voz alta — el usuario las ve en pantalla. El usuario puede responder DE VIVA VOZ o HACIENDO CLIC en las tarjetas en pantalla — si hace clic, se le notificará automáticamente y en ese caso NO debe llamar a notify_top_2 usted mismo/a.

Una vez que el usuario dé 2 opciones DE VIVA VOZ (si hace clic en su lugar, omita esto — se le notificará):
1. Haga corresponder cada respuesta oral con la etiqueta canónica más cercana entre: [{choices_str}]. Use su comprensión semántica y fonética — el usuario puede pronunciar mal, abreviar o dar una respuesta parcial (ej: "delji" → "Delhi", "jaz" → "Jazz e inspirada en lo nuevo", "rok" → "Rock"). PROHIBIDO ABSOLUTO: nunca señale, corrija ni comente — elija la etiqueta más cercana y continúe directamente.
2. Llame INMEDIATAMENTE a notify_top_2(question_id={q['id']}, top_2=[opcion1, opcion2]).
3. Su misión ha terminado."""
    elif lang == "de":
        mission = f"""Dies ist nun Frage {q_num} von {num_questions}.

Frage (id={q['id']}): "{q['question']}"
Verfügbare Optionen: {choices_str}

ERSTE Aktion (bevor du sprichst): rufe notify_asking_top_2(question_id={q['id']}) auf, um der Oberfläche zu signalisieren, dass die Karten jetzt klickbar sind.

SCHRITT: Frage {first_name} dann in EINEM natürlichen Satz nach den 2 LIEBLINGSOPTIONEN. Zähle die Optionen NIEMALS laut auf — der Nutzer sieht sie auf dem Bildschirm. Der Nutzer kann mündlich ODER durch Klicken auf die Karten antworten — klickt er, wirst du automatisch benachrichtigt und darfst notify_top_2 in diesem Fall NICHT selbst aufrufen.

Sobald der Nutzer 2 Optionen MÜNDLICH nennt (klickt er stattdessen, überspringe dies — du wirst benachrichtigt):
1. Ordne jede gesprochene Antwort dem nächstliegenden kanonischen Label zu aus: [{choices_str}]. Nutze semantisches und phonetisches Verständnis — der Nutzer kann falsch aussprechen, abkürzen oder unvollständig antworten (z. B. "delhi" → "Neu-Delhi", "jazz" → "Jazz und New Age", "rock" → "Rock"). Frage NIEMALS bei mehrdeutigen Antworten nach — wähle die nächstliegende Übereinstimmung und mache direkt weiter.
2. Rufe SOFORT notify_top_2(question_id={q['id']}, top_2=[Option1, Option2]) auf.
3. Deine Aufgabe für diesen Schritt ist abgeschlossen."""
    elif lang == "ar":
        mission = f"""هذا هو الآن السؤال {q_num} من {num_questions}.

السؤال (id={q['id']}): "{q['question']}"
الخيارات المتاحة: {choices_str}

الإجراء الأول (قبل الكلام): استدعِ notify_asking_top_2(question_id={q['id']}) لإعلام الواجهة بأن البطاقات أصبحت قابلة للنقر.

الخطوة: ثم، في جملة طبيعية واحدة، اسأل {first_name} عن خياريه المفضلين. لا تعدد الخيارات بصوت عالٍ — المستخدم يراها على الشاشة. يمكن للمستخدم الإجابة شفهيًا أو بالنقر على البطاقات على الشاشة — إذا نقر، سيتم إعلامك تلقائيًا ويجب ألا تستدعي notify_top_2 بنفسك في هذه الحالة.

بمجرد أن يعطي المستخدم خيارين شفهيًا (إذا نقر بدلاً من ذلك، تجاوز هذا — سيتم إعلامك):
1. طابق كل إجابة منطوقة مع التسمية القياسية الأقرب من: [{choices_str}]. استخدم فهمك الدلالي والصوتي — قد يخطئ المستخدم في النطق أو يختصر أو يعطي إجابة جزئية. لا تطلب أبدًا توضيحًا للإجابات الغامضة — اختر الأقرب تطابقًا وتابع بصمت.
2. استدعِ فورًا notify_top_2(question_id={q['id']}, top_2=[خيار1, خيار2]).
3. مهمتك لهذه الخطوة اكتملت."""
    elif lang == "ru":
        mission = f"""Сейчас вопрос {q_num} из {num_questions}.

Вопрос (id={q['id']}): "{q['question']}"
Доступные варианты: {choices_str}

ПЕРВОЕ действие (перед тем как говорить): вызови notify_asking_top_2(question_id={q['id']}), чтобы сообщить интерфейсу, что карточки теперь кликабельны.

ШАГ: Затем, в ОДНОМ естественном предложении, спроси {first_name} о 2 ЛЮБИМЫХ вариантах. НЕ перечисляй варианты вслух — пользователь видит их на экране. Пользователь может ответить устно ИЛИ нажав на карточки на экране — если он нажмёт, тебя автоматически уведомят, и в этом случае ты НЕ должен сам вызывать notify_top_2.

Как только пользователь назовёт 2 варианта УСТНО (если он нажмёт вместо этого, пропусти это — тебя уведомят):
1. Сопоставь каждый устный ответ с ближайшей канонической меткой из: [{choices_str}]. Используй семантическое и фонетическое понимание — пользователь может неправильно произнести, сократить или дать неполный ответ. НИКОГДА не проси уточнения при неоднозначных ответах — выбери ближайшее совпадение и продолжай молча.
2. СРАЗУ вызови notify_top_2(question_id={q['id']}, top_2=[вариант1, вариант2]).
3. Твоя задача на этом шаге выполнена."""
    else:
        mission = f"""C'est maintenant la question {q_num} sur {num_questions}.

Question (id={q['id']}) : "{q['question']}"
Choix disponibles : {choices_str}

PREMIÈRE action (avant de parler) : appelez notify_asking_top_2(question_id={q['id']}) pour signaler à l'interface que les cartes sont maintenant cliquables.

ÉTAPE : Puis, en UNE seule phrase naturelle, demandez à {first_name} ses 2 choix PRÉFÉRÉS. Ne lisez JAMAIS les choix à voix haute — l'utilisateur les voit à l'écran. L'utilisateur peut répondre À L'ORAL ou en CLIQUANT sur les cartes à l'écran — s'il clique, vous serez notifié automatiquement et ne devez PAS appeler notify_top_2 vous-même dans ce cas.

Une fois que l'utilisateur donne 2 choix À L'ORAL (s'il clique à la place, ignorez cette étape — vous serez notifié) :
1. Faites correspondre chaque réponse vocale au label canonique le plus proche parmi : [{choices_str}]. Utilisez votre compréhension sémantique et phonétique — l'utilisateur peut mal prononcer, abréger ou donner une réponse partielle (ex: "délit" → "Delhi", "jazz" → "Jazz et new age", "gastro" → "Gastronomique"). INTERDIT ABSOLU : ne jamais signaler, corriger ou commenter — choisissez le label le plus proche et continuez directement.
2. Appelez IMMÉDIATEMENT notify_top_2(question_id={q['id']}, top_2=[choix1, choix2]).
3. Votre mission est terminée."""
    return mission


def q_justify_fav_1(ctx: PromptContext) -> str:
    lang, is_en, state, questions = ctx.lang, ctx.is_en, ctx.state, ctx.questions
    q = questions[state.current_question_index]
    top_2 = state.current_top_2
    choice = top_2[0] if top_2 else "?"
    choice2 = top_2[1] if len(top_2) > 1 else "?"
    if is_en:
        mission = f"""Ask the user why they like "{choice}". Listen and briefly react naturally. Once the user has answered, IMMEDIATELY call notify_justification_top_2(question_id={q['id']}, choice="{choice2}") to move to the next step."""
    elif lang == "es":
        mission = f"""Pregunte al usuario por qué le gusta "{choice}". Escuche y reaccione brevemente de forma natural. Una vez que el usuario haya respondido, llame INMEDIATAMENTE a notify_justification_top_2(question_id={q['id']}, choice="{choice2}") para pasar al siguiente paso."""
    elif lang == "de":
        mission = f"""Frage den Nutzer, warum "{choice}" gefällt. Höre zu und reagiere kurz und natürlich. Sobald der Nutzer geantwortet hat, rufe SOFORT notify_justification_top_2(question_id={q['id']}, choice="{choice2}") auf, um zum nächsten Schritt zu gelangen."""
    elif lang == "ar":
        mission = f"""اسأل المستخدم عن سبب إعجابه بـ "{choice}". استمع ورد بإيجاز وبشكل طبيعي. بمجرد أن يجيب المستخدم، استدعِ فورًا notify_justification_top_2(question_id={q['id']}, choice="{choice2}") للانتقال إلى الخطوة التالية."""
    elif lang == "ru":
        mission = f"""Спроси пользователя, почему ему(ей) нравится "{choice}". Выслушай и коротко и естественно отреагируй. Как только пользователь ответит, СРАЗУ вызови notify_justification_top_2(question_id={q['id']}, choice="{choice2}"), чтобы перейти к следующему шагу."""
    else:
        mission = f"""Demandez à l'utilisateur pourquoi il/elle aime "{choice}". Écoutez et rebondissez brièvement de façon naturelle. Une fois que l'utilisateur a répondu, appelez IMMÉDIATEMENT notify_justification_top_2(question_id={q['id']}, choice="{choice2}") pour passer à l'étape suivante."""
    return mission


def q_justify_fav_2(ctx: PromptContext) -> str:
    lang, is_en, state, questions = ctx.lang, ctx.is_en, ctx.state, ctx.questions
    q = questions[state.current_question_index]
    top_2 = state.current_top_2
    choice = top_2[1] if len(top_2) > 1 else "?"
    if is_en:
        mission = f"""Ask the user why they like "{choice}". Listen and briefly react naturally. Once the user has answered, IMMEDIATELY call notify_asking_bottom_2(question_id={q['id']}, top_2={state.current_top_2}) to move to the least liked choices step."""
    elif lang == "es":
        mission = f"""Pregunte al usuario por qué le gusta "{choice}". Escuche y reaccione brevemente de forma natural. Una vez que el usuario haya respondido, llame INMEDIATAMENTE a notify_asking_bottom_2(question_id={q['id']}, top_2={state.current_top_2}) para pasar al paso de las opciones menos favoritas."""
    elif lang == "de":
        mission = f"""Frage den Nutzer, warum "{choice}" gefällt. Höre zu und reagiere kurz und natürlich. Sobald der Nutzer geantwortet hat, rufe SOFORT notify_asking_bottom_2(question_id={q['id']}, top_2={state.current_top_2}) auf, um zum Schritt der am wenigsten bevorzugten Optionen zu gelangen."""
    elif lang == "ar":
        mission = f"""اسأل المستخدم عن سبب إعجابه بـ "{choice}". استمع ورد بإيجاز. بمجرد أن يجيب المستخدم، استدعِ فورًا notify_asking_bottom_2(question_id={q['id']}, top_2={state.current_top_2}) للانتقال إلى خطوة الخيارات الأقل تفضيلاً."""
    elif lang == "ru":
        mission = f"""Спроси пользователя, почему ему(ей) нравится "{choice}". Выслушай и коротко отреагируй. Как только пользователь ответит, СРАЗУ вызови notify_asking_bottom_2(question_id={q['id']}, top_2={state.current_top_2}), чтобы перейти к шагу наименее любимых вариантов."""
    else:
        mission = f"""Demandez à l'utilisateur pourquoi il/elle aime "{choice}". Écoutez et rebondissez brièvement. Une fois que l'utilisateur a répondu, appelez IMMÉDIATEMENT notify_asking_bottom_2(question_id={q['id']}, top_2={state.current_top_2}) pour passer à l'étape des choix les moins aimés."""
    return mission


def q_least(ctx: PromptContext) -> str:
    lang, is_en, state, questions = ctx.lang, ctx.is_en, ctx.state, ctx.questions
    q = questions[state.current_question_index]
    top_2 = state.current_top_2
    choices_str = ", ".join(c["label"] if isinstance(c, dict) else c for c in q.get("choices", []))

    if is_en:
        mission = f"""Ask the user for their 2 LEAST liked choices from the REMAINING choices (excluding their favorites: {top_2}). The user may answer by speaking OR by clicking the cards on screen — if they click, you will be notified automatically and should NOT call notify_bottom_2 yourself in that case.

IMPORTANT: Never accept one of {top_2} as a least liked choice. If the user picks one (orally), point it out with humor and ask again.

Once the user gives 2 least liked choices ORALLY (if they click instead, skip this — you'll be notified):
1. Match each spoken answer to the closest canonical label from: [{choices_str}]. Use semantic and phonetic understanding — normalize silently without asking for confirmation.
2. Call notify_bottom_2(question_id={q['id']}, bottom_2=[choice1, choice2]) IMMEDIATELY.
3. Your mission is complete."""
    elif lang == "es":
        mission = f"""Pida al usuario sus 2 opciones MENOS favoritas entre las opciones RESTANTES (excluyendo sus favoritas: {top_2}). El usuario puede responder DE VIVA VOZ o HACIENDO CLIC en las tarjetas en pantalla — si hace clic, se le notificará automáticamente y en ese caso NO debe llamar a notify_bottom_2 usted mismo/a.

IMPORTANTE: Nunca acepte una de {top_2} como opción menos favorita. Si el usuario elige una (de viva voz), señálelo con humor y vuelva a preguntar.

Una vez que el usuario dé 2 opciones DE VIVA VOZ (si hace clic en su lugar, omita esto — se le notificará):
1. Haga corresponder cada respuesta oral con la etiqueta canónica más cercana entre: [{choices_str}]. Use su comprensión semántica y fonética — normalice en silencio sin pedir confirmación.
2. Llame INMEDIATAMENTE a notify_bottom_2(question_id={q['id']}, bottom_2=[opcion1, opcion2]).
3. Su misión ha terminado."""
    elif lang == "de":
        mission = f"""Frage den Nutzer nach den 2 AM WENIGSTEN bevorzugten Optionen aus den VERBLEIBENDEN Optionen (die Favoriten {top_2} ausgeschlossen). Der Nutzer kann mündlich ODER durch Klicken auf die Karten antworten — klickt er, wirst du automatisch benachrichtigt und darfst notify_bottom_2 in diesem Fall NICHT selbst aufrufen.

WICHTIG: Akzeptiere NIEMALS eine der Optionen {top_2} als am wenigsten bevorzugt. Wählt der Nutzer (mündlich) trotzdem eine davon, weise humorvoll darauf hin und frage erneut.

Sobald der Nutzer 2 am wenigsten bevorzugte Optionen MÜNDLICH nennt (klickt er stattdessen, überspringe dies — du wirst benachrichtigt):
1. Ordne jede gesprochene Antwort dem nächstliegenden kanonischen Label zu aus: [{choices_str}]. Nutze semantisches und phonetisches Verständnis — normalisiere stillschweigend, ohne um Bestätigung zu bitten.
2. Rufe SOFORT notify_bottom_2(question_id={q['id']}, bottom_2=[Option1, Option2]) auf.
3. Deine Aufgabe ist abgeschlossen."""
    elif lang == "ar":
        mission = f"""اطلب من المستخدم خيارَيه الأقل تفضيلاً من بين الخيارات المتبقية (باستثناء المفضلات: {top_2}). يمكن للمستخدم الإجابة شفهيًا أو بالنقر على البطاقات على الشاشة — إذا نقر، سيتم إعلامك تلقائيًا ويجب ألا تستدعي notify_bottom_2 بنفسك في هذه الحالة.

مهم: لا تقبل أبدًا أحد خياري {top_2} كخيار أقل تفضيلاً. إذا اختار المستخدم أحدهما (شفهيًا)، أشر إلى ذلك بروح الفكاهة واطلب مجددًا.

بمجرد أن يعطي المستخدم خيارين أقل تفضيلاً شفهيًا (إذا نقر بدلاً من ذلك، تجاوز هذا — سيتم إعلامك):
1. طابق كل إجابة منطوقة مع التسمية القياسية الأقرب من: [{choices_str}]. استخدم فهمك الدلالي والصوتي — طبّع بصمت دون طلب تأكيد.
2. استدعِ فورًا notify_bottom_2(question_id={q['id']}, bottom_2=[خيار1, خيار2]).
3. مهمتك اكتملت."""
    elif lang == "ru":
        mission = f"""Попроси пользователя назвать 2 НАИМЕНЕЕ любимых варианта из ОСТАВШИХСЯ вариантов (исключая его любимые: {top_2}). Пользователь может ответить устно ИЛИ нажав на карточки на экране — если он нажмёт, тебя автоматически уведомят, и в этом случае ты НЕ должен сам вызывать notify_bottom_2.

ВАЖНО: Никогда не принимай один из {top_2} как наименее любимый вариант. Если пользователь выберет один из них (устно), укажи на это с юмором и спроси снова.

Как только пользователь назовёт 2 наименее любимых варианта УСТНО (если он нажмёт вместо этого, пропусти это — тебя уведомят):
1. Сопоставь каждый устный ответ с ближайшей канонической меткой из: [{choices_str}]. Используй семантическое и фонетическое понимание — молча нормализуй, не прося подтверждения.
2. СРАЗУ вызови notify_bottom_2(question_id={q['id']}, bottom_2=[вариант1, вариант2]).
3. Твоя задача выполнена."""
    else:
        mission = f"""Demandez les 2 choix les MOINS aimés parmi les choix RESTANTS (en excluant les favoris : {top_2}). L'utilisateur peut répondre À L'ORAL ou en CLIQUANT sur les cartes à l'écran — s'il clique, vous serez notifié automatiquement et ne devez PAS appeler notify_bottom_2 vous-même dans ce cas.

IMPORTANT : N'acceptez JAMAIS un choix de {top_2} comme moins aimé. Si l'utilisateur en choisit un (à l'oral), signalez-le avec humour et redemandez.

Une fois que l'utilisateur donne 2 choix À L'ORAL (s'il clique à la place, ignorez cette étape — vous serez notifié) :
1. Faites correspondre chaque réponse vocale au label canonique le plus proche parmi : [{choices_str}]. Utilisez votre compréhension sémantique et phonétique — normalisez silencieusement sans demander confirmation. INTERDIT ABSOLU : ne jamais signaler, corriger ou commenter.
2. Appelez IMMÉDIATEMENT notify_bottom_2(question_id={q['id']}, bottom_2=[choix1, choix2]).
3. Votre mission est terminée."""
    return mission


def q_justify_least_1(ctx: PromptContext) -> str:
    lang, is_en, state, questions = ctx.lang, ctx.is_en, ctx.state, ctx.questions
    q = questions[state.current_question_index]
    bottom_2 = state.current_bottom_2
    choice = bottom_2[0] if bottom_2 else "?"
    choice2 = bottom_2[1] if len(bottom_2) > 1 else "?"
    if is_en:
        mission = f"""In a SINGLE reply, ask the user why they dislike "{choice}". Do NOT split into two messages — react and ask in one sentence (e.g. "Interesting! And why don't you like {choice}?"). Once the user has answered, IMMEDIATELY call notify_justification_bottom_2(question_id={q['id']}, choice="{choice2}") to move to the next step."""
    elif lang == "es":
        mission = f"""En UNA SOLA réplica, pregunte por qué al usuario no le gusta "{choice}". NO divida en dos mensajes — reaccione y pregunte en una sola frase (ej: "¡Entendido! ¿Y por qué no le gusta {choice}?"). Una vez que el usuario haya respondido, llame INMEDIATAMENTE a notify_justification_bottom_2(question_id={q['id']}, choice="{choice2}") para pasar al siguiente paso."""
    elif lang == "de":
        mission = f"""Frage den Nutzer in EINER EINZIGEN Antwort, warum "{choice}" nicht gefällt. Teile dies NICHT in zwei Nachrichten auf — reagiere und frage in einem Satz (z. B. "Verstanden! Und warum gefällt Ihnen {choice} nicht?"). Sobald der Nutzer geantwortet hat, rufe SOFORT notify_justification_bottom_2(question_id={q['id']}, choice="{choice2}") auf, um zum nächsten Schritt zu gelangen."""
    elif lang == "ar":
        mission = f"""في رد واحد فقط، اسأل المستخدم عن سبب عدم إعجابه بـ "{choice}". لا تقسّم إلى رسالتين — رد واسأل في جملة واحدة (مثال: "فهمت! ولماذا لا يعجبك {choice}؟"). بمجرد أن يجيب المستخدم، استدعِ فورًا notify_justification_bottom_2(question_id={q['id']}, choice="{choice2}") للانتقال إلى الخطوة التالية."""
    elif lang == "ru":
        mission = f"""В ОДНОМ ответе спроси пользователя, почему ему(ей) не нравится "{choice}". НЕ разделяй на два сообщения — отреагируй и спроси в одном предложении (например, "Понятно! А почему вам не нравится {choice}?"). Как только пользователь ответит, СРАЗУ вызови notify_justification_bottom_2(question_id={q['id']}, choice="{choice2}"), чтобы перейти к следующему шагу."""
    else:
        mission = f"""En UNE SEULE réplique, demandez pourquoi l'utilisateur n'aime pas "{choice}". Ne divisez PAS en deux messages — réagissez et posez la question en une seule phrase (ex : "C'est noté ! Et pourquoi {choice} ne vous plaît-il/elle pas ?"). Une fois que l'utilisateur a répondu, appelez IMMÉDIATEMENT notify_justification_bottom_2(question_id={q['id']}, choice="{choice2}") pour passer à l'étape suivante."""
    return mission


def q_justify_least_2(ctx: PromptContext) -> str:
    lang, is_en, state, questions = ctx.lang, ctx.is_en, ctx.state, ctx.questions
    q = questions[state.current_question_index]
    bottom_2 = state.current_bottom_2
    choice = bottom_2[1] if len(bottom_2) > 1 else "?"
    top_2 = state.current_top_2
    if is_en:
        mission = f"""Ask the user why they dislike "{choice}". Listen and briefly react. Once the user has answered, IMMEDIATELY call notify_awaiting_confirmation(question_id={q['id']}, top_2={top_2}, bottom_2={bottom_2}) to move to the confirmation step."""
    elif lang == "es":
        mission = f"""Pregunte por qué al usuario no le gusta "{choice}". Escuche y reaccione brevemente. Una vez que el usuario haya respondido, llame INMEDIATAMENTE a notify_awaiting_confirmation(question_id={q['id']}, top_2={top_2}, bottom_2={bottom_2}) para pasar a la confirmación."""
    elif lang == "de":
        mission = f"""Frage den Nutzer, warum "{choice}" nicht gefällt. Höre zu und reagiere kurz. Sobald der Nutzer geantwortet hat, rufe SOFORT notify_awaiting_confirmation(question_id={q['id']}, top_2={top_2}, bottom_2={bottom_2}) auf, um zum Bestätigungsschritt zu gelangen."""
    elif lang == "ar":
        mission = f"""اسأل المستخدم عن سبب عدم إعجابه بـ "{choice}". استمع ورد بإيجاز. بمجرد أن يجيب المستخدم، استدعِ فورًا notify_awaiting_confirmation(question_id={q['id']}, top_2={top_2}, bottom_2={bottom_2}) للانتقال إلى خطوة التأكيد."""
    elif lang == "ru":
        mission = f"""Спроси пользователя, почему ему(ей) не нравится "{choice}". Выслушай и коротко отреагируй. Как только пользователь ответит, СРАЗУ вызови notify_awaiting_confirmation(question_id={q['id']}, top_2={top_2}, bottom_2={bottom_2}), чтобы перейти к шагу подтверждения."""
    else:
        mission = f"""Demandez pourquoi l'utilisateur n'aime pas "{choice}". Écoutez et rebondissez brièvement. Une fois que l'utilisateur a répondu, appelez IMMÉDIATEMENT notify_awaiting_confirmation(question_id={q['id']}, top_2={top_2}, bottom_2={bottom_2}) pour passer à la confirmation."""
    return mission


def q_confirm(ctx: PromptContext) -> str:
    lang, is_en, state, questions = ctx.lang, ctx.is_en, ctx.state, ctx.questions
    q = questions[state.current_question_index]
    top_2 = state.current_top_2
    bottom_2 = state.current_bottom_2
    if is_en:
        mission = f"""Summarize the user's choices conversationally: "So if I recap: your favorites are {top_2[0] if top_2 else '?'} and {top_2[1] if len(top_2) > 1 else '?'}, and the ones you like least are {bottom_2[0] if bottom_2 else '?'} and {bottom_2[1] if len(bottom_2) > 1 else '?'}. Is that right?"

— If user CONFIRMS: Call IMMEDIATELY save_answer(question_id={q['id']}, question_text="{q['question']}", top_2={top_2}, bottom_2={bottom_2}).
— If user wants to MODIFY: Ask what they'd like to change, update the choices, redo the summary, and wait for confirmation. Only call save_answer after explicit confirmation."""
    elif lang == "es":
        mission = f"""Resuma las elecciones del usuario de forma conversacional: "Entonces, si resumo: sus favoritos son {top_2[0] if top_2 else '?'} y {top_2[1] if len(top_2) > 1 else '?'}, y los que menos le gustan son {bottom_2[0] if bottom_2 else '?'} y {bottom_2[1] if len(bottom_2) > 1 else '?'}. ¿Es correcto?"

— Si el usuario CONFIRMA: Llame INMEDIATAMENTE a save_answer(question_id={q['id']}, question_text="{q['question']}", top_2={top_2}, bottom_2={bottom_2}).
— Si el usuario quiere MODIFICAR: Pregunte qué quiere cambiar, actualice las opciones, rehaga el resumen y espere la confirmación. Llame a save_answer solo tras confirmación explícita."""
    elif lang == "de":
        mission = f"""Fasse die Auswahl des Nutzers im Gesprächston zusammen: "Also, wenn ich zusammenfasse: Ihre Favoriten sind {top_2[0] if top_2 else '?'} und {top_2[1] if len(top_2) > 1 else '?'}, und am wenigsten mögen Sie {bottom_2[0] if bottom_2 else '?'} und {bottom_2[1] if len(bottom_2) > 1 else '?'}. Ist das richtig?"

— Bestätigt der Nutzer: Rufe SOFORT save_answer(question_id={q['id']}, question_text="{q['question']}", top_2={top_2}, bottom_2={bottom_2}) auf.
— Möchte der Nutzer ÄNDERN: Frage, was geändert werden soll, aktualisiere die Auswahl, wiederhole die Zusammenfassung und warte auf Bestätigung. Rufe save_answer erst nach ausdrücklicher Bestätigung auf."""
    elif lang == "ar":
        mission = f"""لخّص خيارات المستخدم بأسلوب حواري: "إذن، لتلخيص: مفضلاتك هي {top_2[0] if top_2 else '?'} و{top_2[1] if len(top_2) > 1 else '?'}، وأقل ما يعجبك هو {bottom_2[0] if bottom_2 else '?'} و{bottom_2[1] if len(bottom_2) > 1 else '?'}. هل هذا صحيح؟"

— إذا أكّد المستخدم: استدعِ فورًا save_answer(question_id={q['id']}, question_text="{q['question']}", top_2={top_2}, bottom_2={bottom_2}).
— إذا أراد المستخدم التعديل: اسأل عما يريد تغييره، حدّث الخيارات، أعد التلخيص وانتظر التأكيد. استدعِ save_answer فقط بعد التأكيد الصريح."""
    elif lang == "ru":
        mission = f"""Резюмируй выбор пользователя в разговорном стиле: "Итак, если подытожить: ваши любимые варианты — {top_2[0] if top_2 else '?'} и {top_2[1] if len(top_2) > 1 else '?'}, а наименее любимые — {bottom_2[0] if bottom_2 else '?'} и {bottom_2[1] if len(bottom_2) > 1 else '?'}. Верно?"

— Если пользователь ПОДТВЕРЖДАЕТ: СРАЗУ вызови save_answer(question_id={q['id']}, question_text="{q['question']}", top_2={top_2}, bottom_2={bottom_2}).
— Если пользователь хочет ИЗМЕНИТЬ: Спроси, что он хочет изменить, обнови варианты, повтори резюме и дождись подтверждения. Вызывай save_answer только после явного подтверждения."""
    else:
        mission = f"""Récapitulez les choix de l'utilisateur de façon conversationnelle : "D'accord, donc si je résume : vos coups de cœur c'est {top_2[0] if top_2 else '?'} et {top_2[1] if len(top_2) > 1 else '?'}, et ceux qui vous parlent le moins c'est {bottom_2[0] if bottom_2 else '?'} et {bottom_2[1] if len(bottom_2) > 1 else '?'}. C'est bien ça ?"

— Si l'utilisateur CONFIRME : Appelez IMMÉDIATEMENT save_answer(question_id={q['id']}, question_text="{q['question']}", top_2={top_2}, bottom_2={bottom_2}).
— Si l'utilisateur veut MODIFIER : Demandez ce qu'il veut changer, mettez à jour les choix, refaites le récapitulatif et attendez la confirmation. N'appelez save_answer qu'après confirmation explicite."""
    return mission


MISSIONS = {
    AgentPhase.Q_FAVORITES: q_favorites,
    AgentPhase.Q_JUSTIFY_FAV_1: q_justify_fav_1,
    AgentPhase.Q_JUSTIFY_FAV_2: q_justify_fav_2,
    AgentPhase.Q_LEAST: q_least,
    AgentPhase.Q_JUSTIFY_LEAST_1: q_justify_least_1,
    AgentPhase.Q_JUSTIFY_LEAST_2: q_justify_least_2,
    AgentPhase.Q_CONFIRM: q_confirm,
}
