"""Phase 2 — questionnaire, générique selon le format de réponse du questionnaire.

Rien de spécifique à une marque ici : la question vient de la base, et les libellés
(« Vos préférés », « Ce qui vous représente le plus »…), le nombre de choix et les
justifications viennent du format du questionnaire (app/core/answer_format.py).
L'enchaînement des étapes est décidé par le code (app/agent/questionnaire_flow.py).

Pour ajouter une langue : une entrée dans TEMPLATES.
"""
from dataclasses import dataclass

from app.agent.prompts.context import PromptContext
from app.agent.questionnaire_flow import answer_format
from app.agent.state import AgentPhase


@dataclass(frozen=True)
class Templates:
    favorites: str
    least: str
    justify_positive: str
    justify_negative: str
    confirm: str
    choice_word: str   # pour l'exemple d'appel : [choix1, choix2]
    conj: str          # « et »
    count_one: str     # « UNE réponse »
    count_many: str    # « {n} réponses »
    why: str           # « pourquoi il/elle a choisi "{choice}" ({label}) »


TEMPLATES: dict[str, Templates] = {
    "fr": Templates(
        favorites="""C'est maintenant la question {q_num} sur {total}.

Question (id={qid}) : "{question}"
Choix disponibles : {choices}

PREMIÈRE action (avant de parler) : appelez notify_asking_top_2(question_id={qid}) pour signaler à l'interface que les cartes sont maintenant cliquables.

ÉTAPE : Puis, en UNE seule phrase naturelle, demandez à {first_name} de choisir {count} — « {label} ». Ne lisez JAMAIS les choix à voix haute — l'utilisateur les voit à l'écran. L'utilisateur peut répondre À L'ORAL ou en CLIQUANT sur les cartes à l'écran — s'il clique, vous serez notifié automatiquement et ne devez PAS appeler notify_top_2 vous-même dans ce cas.

Une fois que l'utilisateur répond À L'ORAL (s'il clique à la place, ignorez cette étape — vous serez notifié) :
1. Faites correspondre chaque réponse vocale au label canonique le plus proche parmi : [{choices}]. Utilisez votre compréhension sémantique et phonétique — l'utilisateur peut mal prononcer, abréger ou donner une réponse partielle (ex: "délit" → "Delhi", "jazz" → "Jazz et new age", "gastro" → "Gastronomique"). INTERDIT ABSOLU : ne jamais signaler, corriger ou commenter — choisissez le label le plus proche et continuez directement.
2. Appelez IMMÉDIATEMENT notify_top_2(question_id={qid}, top_2={example}).
3. Votre mission est terminée.""",
        least="""Demandez à l'utilisateur de choisir {count} parmi les choix RESTANTS — « {label} » (en excluant : {positives}). L'utilisateur peut répondre À L'ORAL ou en CLIQUANT sur les cartes à l'écran — s'il clique, vous serez notifié automatiquement et ne devez PAS appeler notify_bottom_2 vous-même dans ce cas.

IMPORTANT : N'acceptez JAMAIS un choix de {positives} ici. Si l'utilisateur en choisit un (à l'oral), redemandez simplement, en une phrase courte, parmi les choix restants.

Une fois que l'utilisateur répond À L'ORAL (s'il clique à la place, ignorez cette étape — vous serez notifié) :
1. Faites correspondre chaque réponse vocale au label canonique le plus proche parmi : [{choices}]. Utilisez votre compréhension sémantique et phonétique — normalisez silencieusement sans demander confirmation. INTERDIT ABSOLU : ne jamais signaler, corriger ou commenter.
2. Appelez IMMÉDIATEMENT notify_bottom_2(question_id={qid}, bottom_2={example}).
3. Votre mission est terminée.""",
        justify_positive="""Demandez à l'utilisateur {why}. Écoutez et rebondissez brièvement de façon naturelle. Une fois que l'utilisateur a répondu, appelez IMMÉDIATEMENT justification_done(question_id={qid}) pour passer à l'étape suivante.""",
        justify_negative="""En UNE SEULE réplique, demandez à l'utilisateur {why}. Ne divisez PAS en deux messages — réagissez et posez la question en une seule phrase. Une fois que l'utilisateur a répondu, appelez IMMÉDIATEMENT justification_done(question_id={qid}) pour passer à l'étape suivante.""",
        confirm="""Récapitulez les choix de l'utilisateur de façon conversationnelle : "D'accord, donc si je résume : {recap}. C'est bien ça ?"

— Si l'utilisateur CONFIRME : Appelez IMMÉDIATEMENT save_answer(question_id={qid}, question_text="{question}", top_2={top}, bottom_2={bottom}).
— Si l'utilisateur veut MODIFIER : Demandez ce qu'il veut changer, mettez à jour les choix, refaites le récapitulatif et attendez la confirmation. N'appelez save_answer qu'après confirmation explicite.""",
        choice_word="choix",
        conj=" et ",
        count_one="UNE réponse",
        count_many="{n} réponses",
        why='pourquoi il/elle a choisi "{choice}" ({label})',
    ),
    "en": Templates(
        favorites="""It is now question {q_num} of {total}.

Question (id={qid}): "{question}"
Available choices: {choices}

FIRST action (before speaking): call notify_asking_top_2(question_id={qid}) to signal the interface that the cards are now clickable.

STEP: Then, in ONE natural sentence, ask {first_name} to pick {count} — "{label}". Do NOT enumerate the choices aloud — the user can see them on screen. The user may answer by speaking OR by clicking the cards on screen — if they click, you will be notified automatically and should NOT call notify_top_2 yourself in that case.

Once the user answers ORALLY (if they click instead, skip this — you'll be notified):
1. Match each spoken answer to the closest canonical label from: [{choices}]. Use semantic and phonetic understanding — the user may mispronounce, abbreviate, or give a partial answer (e.g. "delhi" → "Delhi", "jazz" → "Jazz et new age", "rock" → "Rock"). NEVER ask for clarification for ambiguous answers — pick the closest match and move on silently.
2. Call notify_top_2(question_id={qid}, top_2={example}) IMMEDIATELY.
3. Your mission for this step is complete.""",
        least="""Ask the user to pick {count} from the REMAINING choices — "{label}" (excluding: {positives}). The user may answer by speaking OR by clicking the cards on screen — if they click, you will be notified automatically and should NOT call notify_bottom_2 yourself in that case.

IMPORTANT: Never accept one of {positives} here. If the user picks one (orally), simply ask again, in one short sentence, among the remaining choices.

Once the user answers ORALLY (if they click instead, skip this — you'll be notified):
1. Match each spoken answer to the closest canonical label from: [{choices}]. Use semantic and phonetic understanding — normalize silently without asking for confirmation.
2. Call notify_bottom_2(question_id={qid}, bottom_2={example}) IMMEDIATELY.
3. Your mission is complete.""",
        justify_positive="""Ask the user {why}. Listen and briefly react naturally. Once the user has answered, IMMEDIATELY call justification_done(question_id={qid}) to move to the next step.""",
        justify_negative="""In a SINGLE reply, ask the user {why}. Do NOT split into two messages — react and ask in one sentence. Once the user has answered, IMMEDIATELY call justification_done(question_id={qid}) to move to the next step.""",
        confirm="""Summarize the user's choices conversationally: "So if I recap: {recap}. Is that right?"

— If user CONFIRMS: Call IMMEDIATELY save_answer(question_id={qid}, question_text="{question}", top_2={top}, bottom_2={bottom}).
— If user wants to MODIFY: Ask what they'd like to change, update the choices, redo the summary, and wait for confirmation. Only call save_answer after explicit confirmation.""",
        choice_word="choice",
        conj=" and ",
        count_one="ONE answer",
        count_many="{n} answers",
        why='why they chose "{choice}" ({label})',
    ),
    "es": Templates(
        favorites="""Esta es ahora la pregunta {q_num} de {total}.

Pregunta (id={qid}): "{question}"
Opciones disponibles: {choices}

PRIMERA acción (antes de hablar): llame a notify_asking_top_2(question_id={qid}) para indicar a la interfaz que las tarjetas ya son clicables.

PASO: Luego, en UNA sola frase natural, pida a {first_name} que elija {count} — «{label}». NO enumere las opciones en voz alta — el usuario las ve en pantalla. El usuario puede responder DE VIVA VOZ o HACIENDO CLIC en las tarjetas en pantalla — si hace clic, se le notificará automáticamente y en ese caso NO debe llamar a notify_top_2 usted mismo/a.

Una vez que el usuario responda DE VIVA VOZ (si hace clic en su lugar, omita esto — se le notificará):
1. Haga corresponder cada respuesta oral con la etiqueta canónica más cercana entre: [{choices}]. Use su comprensión semántica y fonética — el usuario puede pronunciar mal, abreviar o dar una respuesta parcial. PROHIBIDO ABSOLUTO: nunca señale, corrija ni comente — elija la etiqueta más cercana y continúe directamente.
2. Llame INMEDIATAMENTE a notify_top_2(question_id={qid}, top_2={example}).
3. Su misión ha terminado.""",
        least="""Pida al usuario que elija {count} entre las opciones RESTANTES — «{label}» (excluyendo: {positives}). El usuario puede responder DE VIVA VOZ o HACIENDO CLIC en las tarjetas en pantalla — si hace clic, se le notificará automáticamente y en ese caso NO debe llamar a notify_bottom_2 usted mismo/a.

IMPORTANTE: Nunca acepte una de {positives} aquí. Si el usuario elige una (de viva voz), vuelva a preguntar simplemente, en una frase corta, entre las opciones restantes.

Una vez que el usuario responda DE VIVA VOZ (si hace clic en su lugar, omita esto — se le notificará):
1. Haga corresponder cada respuesta oral con la etiqueta canónica más cercana entre: [{choices}]. Use su comprensión semántica y fonética — normalice en silencio sin pedir confirmación.
2. Llame INMEDIATAMENTE a notify_bottom_2(question_id={qid}, bottom_2={example}).
3. Su misión ha terminado.""",
        justify_positive="""Pregunte al usuario {why}. Escuche y reaccione brevemente de forma natural. Una vez que el usuario haya respondido, llame INMEDIATAMENTE a justification_done(question_id={qid}) para pasar al siguiente paso.""",
        justify_negative="""En UNA SOLA réplica, pregunte al usuario {why}. NO divida en dos mensajes — reaccione y pregunte en una sola frase. Una vez que el usuario haya respondido, llame INMEDIATAMENTE a justification_done(question_id={qid}) para pasar al siguiente paso.""",
        confirm="""Resuma las elecciones del usuario de forma conversacional: "Entonces, si resumo: {recap}. ¿Es correcto?"

— Si el usuario CONFIRMA: Llame INMEDIATAMENTE a save_answer(question_id={qid}, question_text="{question}", top_2={top}, bottom_2={bottom}).
— Si el usuario quiere MODIFICAR: Pregunte qué quiere cambiar, actualice las opciones, rehaga el resumen y espere la confirmación. Llame a save_answer solo tras confirmación explícita.""",
        choice_word="opcion",
        conj=" y ",
        count_one="UNA respuesta",
        count_many="{n} respuestas",
        why='por qué eligió "{choice}" ({label})',
    ),
    "de": Templates(
        favorites="""Dies ist nun Frage {q_num} von {total}.

Frage (id={qid}): "{question}"
Verfügbare Optionen: {choices}

ERSTE Aktion (bevor du sprichst): rufe notify_asking_top_2(question_id={qid}) auf, um der Oberfläche zu signalisieren, dass die Karten jetzt klickbar sind.

SCHRITT: Bitte {first_name} dann in EINEM natürlichen Satz, {count} zu wählen — „{label}“. Zähle die Optionen NIEMALS laut auf — der Nutzer sieht sie auf dem Bildschirm. Der Nutzer kann mündlich ODER durch Klicken auf die Karten antworten — klickt er, wirst du automatisch benachrichtigt und darfst notify_top_2 in diesem Fall NICHT selbst aufrufen.

Sobald der Nutzer MÜNDLICH antwortet (klickt er stattdessen, überspringe dies — du wirst benachrichtigt):
1. Ordne jede gesprochene Antwort dem nächstliegenden kanonischen Label zu aus: [{choices}]. Nutze semantisches und phonetisches Verständnis — der Nutzer kann falsch aussprechen, abkürzen oder unvollständig antworten. Frage NIEMALS bei mehrdeutigen Antworten nach — wähle die nächstliegende Übereinstimmung und mache direkt weiter.
2. Rufe SOFORT notify_top_2(question_id={qid}, top_2={example}) auf.
3. Deine Aufgabe für diesen Schritt ist abgeschlossen.""",
        least="""Bitte den Nutzer, {count} aus den VERBLEIBENDEN Optionen zu wählen — „{label}“ (ausgeschlossen: {positives}). Der Nutzer kann mündlich ODER durch Klicken auf die Karten antworten — klickt er, wirst du automatisch benachrichtigt und darfst notify_bottom_2 in diesem Fall NICHT selbst aufrufen.

WICHTIG: Akzeptiere hier NIEMALS eine der Optionen {positives}. Wählt der Nutzer (mündlich) trotzdem eine davon, frage einfach in einem kurzen Satz erneut unter den verbleibenden Optionen.

Sobald der Nutzer MÜNDLICH antwortet (klickt er stattdessen, überspringe dies — du wirst benachrichtigt):
1. Ordne jede gesprochene Antwort dem nächstliegenden kanonischen Label zu aus: [{choices}]. Nutze semantisches und phonetisches Verständnis — normalisiere stillschweigend, ohne um Bestätigung zu bitten.
2. Rufe SOFORT notify_bottom_2(question_id={qid}, bottom_2={example}) auf.
3. Deine Aufgabe ist abgeschlossen.""",
        justify_positive="""Frage den Nutzer, {why}. Höre zu und reagiere kurz und natürlich. Sobald der Nutzer geantwortet hat, rufe SOFORT justification_done(question_id={qid}) auf, um zum nächsten Schritt zu gelangen.""",
        justify_negative="""Frage den Nutzer in EINER EINZIGEN Antwort, {why}. Teile dies NICHT in zwei Nachrichten auf — reagiere und frage in einem Satz. Sobald der Nutzer geantwortet hat, rufe SOFORT justification_done(question_id={qid}) auf, um zum nächsten Schritt zu gelangen.""",
        confirm="""Fasse die Auswahl des Nutzers im Gesprächston zusammen: "Also, wenn ich zusammenfasse: {recap}. Ist das richtig?"

— Bestätigt der Nutzer: Rufe SOFORT save_answer(question_id={qid}, question_text="{question}", top_2={top}, bottom_2={bottom}) auf.
— Möchte der Nutzer ÄNDERN: Frage, was geändert werden soll, aktualisiere die Auswahl, wiederhole die Zusammenfassung und warte auf Bestätigung. Rufe save_answer erst nach ausdrücklicher Bestätigung auf.""",
        choice_word="Option",
        conj=" und ",
        count_one="EINE Antwort",
        count_many="{n} Antworten",
        why='warum er/sie "{choice}" gewählt hat ({label})',
    ),
    "ar": Templates(
        favorites="""هذا هو الآن السؤال {q_num} من {total}.

السؤال (id={qid}): "{question}"
الخيارات المتاحة: {choices}

الإجراء الأول (قبل الكلام): استدعِ notify_asking_top_2(question_id={qid}) لإعلام الواجهة بأن البطاقات أصبحت قابلة للنقر.

الخطوة: ثم، في جملة طبيعية واحدة، اطلب من {first_name} اختيار {count} — «{label}». لا تعدد الخيارات بصوت عالٍ — المستخدم يراها على الشاشة. يمكن للمستخدم الإجابة شفهيًا أو بالنقر على البطاقات على الشاشة — إذا نقر، سيتم إعلامك تلقائيًا ويجب ألا تستدعي notify_top_2 بنفسك في هذه الحالة.

بمجرد أن يجيب المستخدم شفهيًا (إذا نقر بدلاً من ذلك، تجاوز هذا — سيتم إعلامك):
1. طابق كل إجابة منطوقة مع التسمية القياسية الأقرب من: [{choices}]. استخدم فهمك الدلالي والصوتي — قد يخطئ المستخدم في النطق أو يختصر أو يعطي إجابة جزئية. لا تطلب أبدًا توضيحًا للإجابات الغامضة — اختر الأقرب تطابقًا وتابع بصمت.
2. استدعِ فورًا notify_top_2(question_id={qid}, top_2={example}).
3. مهمتك لهذه الخطوة اكتملت.""",
        least="""اطلب من المستخدم اختيار {count} من بين الخيارات المتبقية — «{label}» (باستثناء: {positives}). يمكن للمستخدم الإجابة شفهيًا أو بالنقر على البطاقات على الشاشة — إذا نقر، سيتم إعلامك تلقائيًا ويجب ألا تستدعي notify_bottom_2 بنفسك في هذه الحالة.

مهم: لا تقبل أبدًا أحد الخيارات {positives} هنا. إذا اختار المستخدم أحدها (شفهيًا)، اطلب مجددًا ببساطة، بجملة قصيرة، من بين الخيارات المتبقية.

بمجرد أن يجيب المستخدم شفهيًا (إذا نقر بدلاً من ذلك، تجاوز هذا — سيتم إعلامك):
1. طابق كل إجابة منطوقة مع التسمية القياسية الأقرب من: [{choices}]. استخدم فهمك الدلالي والصوتي — طبّع بصمت دون طلب تأكيد.
2. استدعِ فورًا notify_bottom_2(question_id={qid}, bottom_2={example}).
3. مهمتك اكتملت.""",
        justify_positive="""اسأل المستخدم {why}. استمع ورد بإيجاز وبشكل طبيعي. بمجرد أن يجيب المستخدم، استدعِ فورًا justification_done(question_id={qid}) للانتقال إلى الخطوة التالية.""",
        justify_negative="""في رد واحد فقط، اسأل المستخدم {why}. لا تقسّم إلى رسالتين — رد واسأل في جملة واحدة. بمجرد أن يجيب المستخدم، استدعِ فورًا justification_done(question_id={qid}) للانتقال إلى الخطوة التالية.""",
        confirm="""لخّص خيارات المستخدم بأسلوب حواري: "إذن، لتلخيص: {recap}. هل هذا صحيح؟"

— إذا أكّد المستخدم: استدعِ فورًا save_answer(question_id={qid}, question_text="{question}", top_2={top}, bottom_2={bottom}).
— إذا أراد المستخدم التعديل: اسأل عما يريد تغييره، حدّث الخيارات، أعد التلخيص وانتظر التأكيد. استدعِ save_answer فقط بعد التأكيد الصريح.""",
        choice_word="خيار",
        conj=" و",
        count_one="إجابة واحدة",
        count_many="{n} إجابات",
        why='عن سبب اختياره "{choice}" ({label})',
    ),
    "ru": Templates(
        favorites="""Сейчас вопрос {q_num} из {total}.

Вопрос (id={qid}): "{question}"
Доступные варианты: {choices}

ПЕРВОЕ действие (перед тем как говорить): вызови notify_asking_top_2(question_id={qid}), чтобы сообщить интерфейсу, что карточки теперь кликабельны.

ШАГ: Затем, в ОДНОМ естественном предложении, попроси {first_name} выбрать {count} — «{label}». НЕ перечисляй варианты вслух — пользователь видит их на экране. Пользователь может ответить устно ИЛИ нажав на карточки на экране — если он нажмёт, тебя автоматически уведомят, и в этом случае ты НЕ должен сам вызывать notify_top_2.

Как только пользователь ответит УСТНО (если он нажмёт вместо этого, пропусти это — тебя уведомят):
1. Сопоставь каждый устный ответ с ближайшей канонической меткой из: [{choices}]. Используй семантическое и фонетическое понимание — пользователь может неправильно произнести, сократить или дать неполный ответ. НИКОГДА не проси уточнения при неоднозначных ответах — выбери ближайшее совпадение и продолжай молча.
2. СРАЗУ вызови notify_top_2(question_id={qid}, top_2={example}).
3. Твоя задача на этом шаге выполнена.""",
        least="""Попроси пользователя выбрать {count} из ОСТАВШИХСЯ вариантов — «{label}» (исключая: {positives}). Пользователь может ответить устно ИЛИ нажав на карточки на экране — если он нажмёт, тебя автоматически уведомят, и в этом случае ты НЕ должен сам вызывать notify_bottom_2.

ВАЖНО: Никогда не принимай здесь один из {positives}. Если пользователь выберет один из них (устно), просто переспроси одной короткой фразой среди оставшихся вариантов.

Как только пользователь ответит УСТНО (если он нажмёт вместо этого, пропусти это — тебя уведомят):
1. Сопоставь каждый устный ответ с ближайшей канонической меткой из: [{choices}]. Используй семантическое и фонетическое понимание — молча нормализуй, не прося подтверждения.
2. СРАЗУ вызови notify_bottom_2(question_id={qid}, bottom_2={example}).
3. Твоя задача выполнена.""",
        justify_positive="""Спроси пользователя, {why}. Выслушай и коротко и естественно отреагируй. Как только пользователь ответит, СРАЗУ вызови justification_done(question_id={qid}), чтобы перейти к следующему шагу.""",
        justify_negative="""В ОДНОМ ответе спроси пользователя, {why}. НЕ разделяй на два сообщения — отреагируй и спроси в одном предложении. Как только пользователь ответит, СРАЗУ вызови justification_done(question_id={qid}), чтобы перейти к следующему шагу.""",
        confirm="""Резюмируй выбор пользователя в разговорном стиле: "Итак, если подытожить: {recap}. Верно?"

— Если пользователь ПОДТВЕРЖДАЕТ: СРАЗУ вызови save_answer(question_id={qid}, question_text="{question}", top_2={top}, bottom_2={bottom}).
— Если пользователь хочет ИЗМЕНИТЬ: Спроси, что он хочет изменить, обнови варианты, повтори резюме и дождись подтверждения. Вызывай save_answer только после явного подтверждения.""",
        choice_word="вариант",
        conj=" и ",
        count_one="ОДИН ответ",
        count_many="{n} ответа",
        why='почему он(а) выбрал(а) "{choice}" ({label})',
    ),
}


# Réponse par numéro : chaque carte porte un numéro à l'écran.
NUMBER_HINT: dict[str, str] = {
    "fr": "L'utilisateur peut aussi répondre par le NUMÉRO affiché sur la carte (« le 4 », « le choix numéro 4 », « 4 ») : passez alors le libellé correspondant (ou simplement le numéro). Ne commentez JAMAIS la formulation ou la prononciation de l'utilisateur, et ne lisez jamais la liste des choix à voix haute.",
    "en": "The user may also answer with the NUMBER shown on the card (\"number 4\", \"the 4th one\", \"4\"): pass the matching label (or just the number). NEVER comment on the user's wording or pronunciation, and never read the list of choices aloud.",
    "es": "El usuario también puede responder con el NÚMERO de la tarjeta («el 4», «la opción número 4», «4»): pase la etiqueta correspondiente (o solo el número). NUNCA comente la formulación o la pronunciación del usuario, y nunca lea la lista de opciones en voz alta.",
    "de": "Der Nutzer kann auch mit der NUMMER auf der Karte antworten („die 4“, „Nummer 4“, „4“): übergib dann das passende Label (oder einfach die Nummer). Kommentiere NIEMALS die Formulierung oder Aussprache des Nutzers und lies die Optionen nie laut vor.",
    "ar": "يمكن للمستخدم أيضًا الإجابة برقم البطاقة («رقم 4»، «4»): مرّر التسمية المطابقة (أو الرقم فقط). لا تعلّق أبدًا على صياغة المستخدم أو نطقه، ولا تقرأ قائمة الخيارات بصوت عالٍ.",
    "ru": "Пользователь может также ответить НОМЕРОМ карточки («четвёртый», «номер 4», «4»): передай соответствующую метку (или просто номер). НИКОГДА не комментируй формулировку или произношение пользователя и не зачитывай варианты вслух.",
}


# Étape « le moins » : seuls les choix restants, avec LEUR numéro de carte (jamais renumérotés).
REMAINING_HINT: dict[str, str] = {
    "fr": "Choix restants, avec le numéro de leur carte à l'écran : {remaining}. Les numéros sont ceux des cartes : ne les renumérotez JAMAIS (si l'utilisateur dit « le 3 », c'est la carte n°3, même si ce n'est pas le 3e choix restant).",
    "en": "Remaining choices, with their card number on screen: {remaining}. Numbers are the card numbers: NEVER renumber them (if the user says \"number 3\", it is card #3, even if it is not the 3rd remaining choice).",
    "es": "Opciones restantes, con el número de su tarjeta en pantalla: {remaining}. Los números son los de las tarjetas: NUNCA los renumere (si el usuario dice «el 3», es la tarjeta n.º 3, aunque no sea la 3.ª opción restante).",
    "de": "Verbleibende Optionen mit ihrer Kartennummer auf dem Bildschirm: {remaining}. Die Nummern sind die der Karten: NIEMALS neu nummerieren (sagt der Nutzer „die 3“, ist es Karte Nr. 3, auch wenn sie nicht die 3. verbleibende Option ist).",
    "ar": "الخيارات المتبقية مع رقم بطاقتها على الشاشة: {remaining}. الأرقام هي أرقام البطاقات: لا تُعِد ترقيمها أبدًا (إذا قال المستخدم «رقم 3» فهي البطاقة رقم 3، حتى لو لم تكن الخيار المتبقي الثالث).",
    "ru": "Оставшиеся варианты с номером их карточки на экране: {remaining}. Номера — это номера карточек: НИКОГДА не перенумеровывай их (если пользователь говорит «третий», это карточка №3, даже если это не третий из оставшихся).",
}

# Justification : vraie question « pourquoi », et prise en compte d'un changement d'avis.
JUSTIFY_HINT: dict[str, str] = {
    "fr": "Votre question DOIT commencer par « Pourquoi » et citer le choix, en une seule phrase, sans phrase de remplissage (pas de « je vais enregistrer cela »). Si, au lieu de justifier, l'utilisateur donne un AUTRE choix (un libellé ou un numéro de carte), il change d'avis : n'appelez PAS justification_done, appelez {tool}(question_id={qid}, {param}=[...]) avec la liste COMPLÈTE de ses choix « {label} » ({count}).",
    "en": "Your question MUST start with \"Why\" and name the choice, in a single sentence, with no filler (no \"I'll save that\"). If, instead of explaining, the user gives ANOTHER choice (a label or a card number), they changed their mind: do NOT call justification_done, call {tool}(question_id={qid}, {param}=[...]) with the COMPLETE list of their \"{label}\" choices ({count}).",
    "es": "Su pregunta DEBE empezar por «Por qué» y citar la opción, en una sola frase, sin relleno (nada de «voy a guardarlo»). Si, en lugar de justificar, el usuario da OTRA opción (una etiqueta o un número de tarjeta), cambió de opinión: NO llame a justification_done, llame a {tool}(question_id={qid}, {param}=[...]) con la lista COMPLETA de sus opciones «{label}» ({count}).",
    "de": "Deine Frage MUSS mit „Warum“ beginnen und die Option nennen, in einem einzigen Satz, ohne Füllsätze (kein „ich speichere das“). Nennt der Nutzer statt einer Begründung eine ANDERE Option (ein Label oder eine Kartennummer), hat er seine Meinung geändert: rufe NICHT justification_done auf, sondern {tool}(question_id={qid}, {param}=[...]) mit der VOLLSTÄNDIGEN Liste seiner Optionen „{label}“ ({count}).",
    "ar": "يجب أن يبدأ سؤالك بـ«لماذا» وأن يذكر الخيار، في جملة واحدة، دون حشو (لا «سأسجل ذلك»). إذا أعطى المستخدم خيارًا آخر بدل التبرير (تسمية أو رقم بطاقة)، فقد غيّر رأيه: لا تستدعِ justification_done، بل استدعِ {tool}(question_id={qid}, {param}=[...]) بالقائمة الكاملة لخياراته «{label}» ({count}).",
    "ru": "Твой вопрос ДОЛЖЕН начинаться с «Почему» и называть выбор, одним предложением, без лишних фраз (никаких «я это запишу»). Если вместо объяснения пользователь называет ДРУГОЙ вариант (метку или номер карточки), он передумал: НЕ вызывай justification_done, вызови {tool}(question_id={qid}, {param}=[...]) с ПОЛНЫМ списком его вариантов «{label}» ({count}).",
}


def _hint(table: dict[str, str], lang: str, **values) -> str:
    return "\n\n" + table.get(lang, table["fr"]).format(**values)


# ── Construction ─────────────────────────────────────────────────────────

def _parts(ctx: PromptContext) -> tuple[Templates, dict]:
    lang = ctx.lang if ctx.lang in TEMPLATES else "fr"
    q = ctx.questions[ctx.state.current_question_index]
    labels = [c["label"] if isinstance(c, dict) else c for c in q.get("choices", [])]
    # Numérotés comme les pastilles affichées sur les cartes (1, 2, 3…)
    choices = _numbered(enumerate(labels, 1))
    base = {
        "qid": q["id"],
        "question": q["question"],
        "choices": choices,
        "q_num": ctx.state.current_question_index + 1,
        "total": ctx.num_questions,
        "first_name": ctx.state.profile.get("first_name", ""),
    }
    return TEMPLATES[lang], base


def _numbered(pairs) -> str:
    return " ; ".join(f"{i}. {label}" for i, label in pairs)


def _remaining(ctx: PromptContext) -> str:
    """Choix non retenus en « le plus », avec leur numéro de carte d'origine."""
    q = ctx.questions[ctx.state.current_question_index]
    labels = [c["label"] if isinstance(c, dict) else c for c in q.get("choices", [])]
    taken = {l.strip().lower() for l in ctx.state.current_top_2}
    return _numbered((i, l) for i, l in enumerate(labels, 1) if l.strip().lower() not in taken)


def _count(tpl: Templates, n: int) -> str:
    return tpl.count_one if n == 1 else tpl.count_many.format(n=n)


def _example(tpl: Templates, n: int) -> str:
    return "[" + ", ".join(f"{tpl.choice_word}{i + 1}" for i in range(n)) + "]"


def _items(tpl: Templates, items: list[str]) -> str:
    items = items or ["?"]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + tpl.conj + items[-1]


def _current(items: list[str], index: int) -> str:
    return items[index] if index < len(items) else "?"


def q_favorites(ctx: PromptContext) -> str:
    tpl, b = _parts(ctx)
    fmt = answer_format(ctx.config)
    n = fmt.positive_count
    mission = tpl.favorites.format(**b, count=_count(tpl, n), label=fmt.positive_label, example=_example(tpl, n))
    return mission + "\n\n" + NUMBER_HINT.get(ctx.lang, NUMBER_HINT["fr"])


def q_least(ctx: PromptContext) -> str:
    tpl, b = _parts(ctx)
    fmt = answer_format(ctx.config)
    n = fmt.negative_count
    mission = tpl.least.format(
        **b, count=_count(tpl, n), label=fmt.negative_label, example=_example(tpl, n),
        positives=ctx.state.current_top_2,
    )
    return (mission + "\n\n" + NUMBER_HINT.get(ctx.lang, NUMBER_HINT["fr"])
            + _hint(REMAINING_HINT, ctx.lang, remaining=_remaining(ctx)))


def q_justify_positive(ctx: PromptContext) -> str:
    tpl, b = _parts(ctx)
    choice = _current(ctx.state.current_top_2, ctx.state.justify_index)
    fmt = answer_format(ctx.config)
    label = fmt.positive_label
    mission = tpl.justify_positive.format(**b, why=tpl.why.format(choice=choice, label=label))
    return mission + _hint(JUSTIFY_HINT, ctx.lang, tool="notify_top_2", param="top_2", qid=b["qid"],
                           label=label, count=_count(tpl, fmt.positive_count))


def q_justify_negative(ctx: PromptContext) -> str:
    tpl, b = _parts(ctx)
    choice = _current(ctx.state.current_bottom_2, ctx.state.justify_index)
    fmt = answer_format(ctx.config)
    label = fmt.negative_label
    mission = tpl.justify_negative.format(**b, why=tpl.why.format(choice=choice, label=label))
    return mission + _hint(JUSTIFY_HINT, ctx.lang, tool="notify_bottom_2", param="bottom_2", qid=b["qid"],
                           label=label, count=_count(tpl, fmt.negative_count))


def q_confirm(ctx: PromptContext) -> str:
    tpl, b = _parts(ctx)
    fmt = answer_format(ctx.config)
    top, bottom = ctx.state.current_top_2, ctx.state.current_bottom_2
    recap = f"{fmt.positive_label} : {_items(tpl, top)}"
    if fmt.negative_count > 0:
        recap += f" ; {fmt.negative_label} : {_items(tpl, bottom)}"
    return tpl.confirm.format(**b, recap=recap, top=top, bottom=bottom)


MISSIONS = {
    AgentPhase.Q_FAVORITES: q_favorites,
    AgentPhase.Q_JUSTIFY_POSITIVE: q_justify_positive,
    AgentPhase.Q_LEAST: q_least,
    AgentPhase.Q_JUSTIFY_NEGATIVE: q_justify_negative,
    AgentPhase.Q_CONFIRM: q_confirm,
}
