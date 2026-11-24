"""Phase 2 — questionnaire, générique selon le format de réponse du questionnaire.

Deux cadrages (`framing`) :
  preference : « vos choix préférés / les moins aimés »         (Lylo, Ester)
  trait      : « ce qui vous représente le plus / le moins »    (Help)
Le nombre de choix et les justifications viennent du format (app/core/answer_format.py) ;
l'enchaînement des étapes est décidé par le code (app/agent/questionnaire_flow.py).

Pour ajouter une langue : une entrée dans WORDING (par cadrage) et dans TEMPLATES.
"""
from dataclasses import dataclass
from typing import Callable

from app.agent.prompts.context import PromptContext
from app.agent.questionnaire_flow import answer_format
from app.agent.state import AgentPhase


@dataclass(frozen=True)
class Wording:
    ask_positive: Callable[[int], str]   # « ses 2 choix PRÉFÉRÉS »
    ask_negative: Callable[[int], str]   # « ses 2 choix les MOINS aimés »
    why_positive: str                    # « pourquoi il/elle aime "{choice}" »
    why_negative: str
    recap_positive: str                  # « vos coups de cœur c'est {items} »
    recap_negative: str                  # commence par sa conjonction (« et ceux qui… »)


def _n(n: int, one: str, many: str) -> str:
    return one if n == 1 else many.format(n=n)


WORDING: dict[str, dict[str, Wording]] = {
    "preference": {
        "fr": Wording(
            ask_positive=lambda n: _n(n, "son choix PRÉFÉRÉ", "ses {n} choix PRÉFÉRÉS"),
            ask_negative=lambda n: _n(n, "son choix le MOINS aimé", "ses {n} choix les MOINS aimés"),
            why_positive='pourquoi il/elle aime "{choice}"',
            why_negative='pourquoi il/elle n\'aime pas "{choice}"',
            recap_positive="vos coups de cœur c'est {items}",
            recap_negative="et ceux qui vous parlent le moins c'est {items}",
        ),
        "en": Wording(
            ask_positive=lambda n: _n(n, "their FAVORITE choice", "their {n} FAVORITE choices"),
            ask_negative=lambda n: _n(n, "their LEAST liked choice", "their {n} LEAST liked choices"),
            why_positive='why they like "{choice}"',
            why_negative='why they dislike "{choice}"',
            recap_positive="your favorites are {items}",
            recap_negative="and the ones you like least are {items}",
        ),
        "es": Wording(
            ask_positive=lambda n: _n(n, "su opción FAVORITA", "sus {n} opciones FAVORITAS"),
            ask_negative=lambda n: _n(n, "su opción MENOS favorita", "sus {n} opciones MENOS favoritas"),
            why_positive='por qué le gusta "{choice}"',
            why_negative='por qué no le gusta "{choice}"',
            recap_positive="sus favoritos son {items}",
            recap_negative="y los que menos le gustan son {items}",
        ),
        "de": Wording(
            ask_positive=lambda n: _n(n, "die LIEBLINGSOPTION", "die {n} LIEBLINGSOPTIONEN"),
            ask_negative=lambda n: _n(n, "die AM WENIGSTEN bevorzugte Option", "die {n} AM WENIGSTEN bevorzugten Optionen"),
            why_positive='warum "{choice}" gefällt',
            why_negative='warum "{choice}" nicht gefällt',
            recap_positive="Ihre Favoriten sind {items}",
            recap_negative="und am wenigsten mögen Sie {items}",
        ),
        "ar": Wording(
            ask_positive=lambda n: _n(n, "خياره المفضل", "خياراته المفضلة الـ{n}"),
            ask_negative=lambda n: _n(n, "خياره الأقل تفضيلاً", "خياراته الأقل تفضيلاً الـ{n}"),
            why_positive='عن سبب إعجابه بـ "{choice}"',
            why_negative='عن سبب عدم إعجابه بـ "{choice}"',
            recap_positive="مفضلاتك هي {items}",
            recap_negative="وأقل ما يعجبك هو {items}",
        ),
        "ru": Wording(
            ask_positive=lambda n: _n(n, "его (её) ЛЮБИМЫЙ вариант", "его (её) {n} ЛЮБИМЫХ варианта"),
            ask_negative=lambda n: _n(n, "его (её) НАИМЕНЕЕ любимый вариант", "его (её) {n} НАИМЕНЕЕ любимых варианта"),
            why_positive='почему ему(ей) нравится "{choice}"',
            why_negative='почему ему(ей) не нравится "{choice}"',
            recap_positive="ваши любимые варианты — {items}",
            recap_negative="а наименее любимые — {items}",
        ),
    },
    "trait": {
        "fr": Wording(
            ask_positive=lambda n: _n(n, "l'option qui le/la REPRÉSENTE LE PLUS", "les {n} options qui le/la REPRÉSENTENT LE PLUS"),
            ask_negative=lambda n: _n(n, "l'option qui le/la représente LE MOINS", "les {n} options qui le/la représentent LE MOINS"),
            why_positive='pourquoi "{choice}" le/la représente',
            why_negative='pourquoi "{choice}" ne le/la représente pas',
            recap_positive="ce qui vous représente le plus c'est {items}",
            recap_negative="et ce qui vous représente le moins c'est {items}",
        ),
        "en": Wording(
            ask_positive=lambda n: _n(n, "the option that describes them BEST", "the {n} options that describe them BEST"),
            ask_negative=lambda n: _n(n, "the option that describes them LEAST", "the {n} options that describe them LEAST"),
            why_positive='why "{choice}" describes them',
            why_negative='why "{choice}" does not describe them',
            recap_positive="what describes you best is {items}",
            recap_negative="and what describes you least is {items}",
        ),
        "es": Wording(
            ask_positive=lambda n: _n(n, "la opción que MEJOR le describe", "las {n} opciones que MEJOR le describen"),
            ask_negative=lambda n: _n(n, "la opción que MENOS le describe", "las {n} opciones que MENOS le describen"),
            why_positive='por qué "{choice}" le describe',
            why_negative='por qué "{choice}" no le describe',
            recap_positive="lo que mejor le describe es {items}",
            recap_negative="y lo que menos le describe es {items}",
        ),
        "de": Wording(
            ask_positive=lambda n: _n(n, "die Option, die AM BESTEN zu ihm/ihr passt", "die {n} Optionen, die AM BESTEN zu ihm/ihr passen"),
            ask_negative=lambda n: _n(n, "die Option, die AM WENIGSTEN zu ihm/ihr passt", "die {n} Optionen, die AM WENIGSTEN zu ihm/ihr passen"),
            why_positive='warum "{choice}" zu ihm/ihr passt',
            why_negative='warum "{choice}" nicht zu ihm/ihr passt',
            recap_positive="am besten beschreibt Sie {items}",
            recap_negative="und am wenigsten beschreibt Sie {items}",
        ),
        "ar": Wording(
            ask_positive=lambda n: _n(n, "الخيار الذي يمثّله أكثر", "الخيارات الـ{n} التي تمثّله أكثر"),
            ask_negative=lambda n: _n(n, "الخيار الذي يمثّله أقل", "الخيارات الـ{n} التي تمثّله أقل"),
            why_positive='عن سبب كون "{choice}" يمثّله',
            why_negative='عن سبب كون "{choice}" لا يمثّله',
            recap_positive="ما يمثّلك أكثر هو {items}",
            recap_negative="وما يمثّلك أقل هو {items}",
        ),
        "ru": Wording(
            ask_positive=lambda n: _n(n, "вариант, который ЛУЧШЕ ВСЕГО его (её) описывает", "{n} варианта, которые ЛУЧШЕ ВСЕГО его (её) описывают"),
            ask_negative=lambda n: _n(n, "вариант, который МЕНЬШЕ ВСЕГО его (её) описывает", "{n} варианта, которые МЕНЬШЕ ВСЕГО его (её) описывают"),
            why_positive='почему "{choice}" его (её) описывает',
            why_negative='почему "{choice}" его (её) не описывает',
            recap_positive="лучше всего вас описывает {items}",
            recap_negative="а меньше всего — {items}",
        ),
    },
}


@dataclass(frozen=True)
class Templates:
    favorites: str
    least: str
    justify_positive: str
    justify_negative: str
    confirm: str
    choice_word: str   # pour l'exemple d'appel : [choix1, choix2]
    conj: str          # « et »


TEMPLATES: dict[str, Templates] = {
    "fr": Templates(
        favorites="""C'est maintenant la question {q_num} sur {total}.

Question (id={qid}) : "{question}"
Choix disponibles : {choices}

PREMIÈRE action (avant de parler) : appelez notify_asking_top_2(question_id={qid}) pour signaler à l'interface que les cartes sont maintenant cliquables.

ÉTAPE : Puis, en UNE seule phrase naturelle, demandez à {first_name} {ask}. Ne lisez JAMAIS les choix à voix haute — l'utilisateur les voit à l'écran. L'utilisateur peut répondre À L'ORAL ou en CLIQUANT sur les cartes à l'écran — s'il clique, vous serez notifié automatiquement et ne devez PAS appeler notify_top_2 vous-même dans ce cas.

Une fois que l'utilisateur répond À L'ORAL (s'il clique à la place, ignorez cette étape — vous serez notifié) :
1. Faites correspondre chaque réponse vocale au label canonique le plus proche parmi : [{choices}]. Utilisez votre compréhension sémantique et phonétique — l'utilisateur peut mal prononcer, abréger ou donner une réponse partielle (ex: "délit" → "Delhi", "jazz" → "Jazz et new age", "gastro" → "Gastronomique"). INTERDIT ABSOLU : ne jamais signaler, corriger ou commenter — choisissez le label le plus proche et continuez directement.
2. Appelez IMMÉDIATEMENT notify_top_2(question_id={qid}, top_2={example}).
3. Votre mission est terminée.""",
        least="""Demandez {ask} parmi les choix RESTANTS (en excluant : {positives}). L'utilisateur peut répondre À L'ORAL ou en CLIQUANT sur les cartes à l'écran — s'il clique, vous serez notifié automatiquement et ne devez PAS appeler notify_bottom_2 vous-même dans ce cas.

IMPORTANT : N'acceptez JAMAIS un choix de {positives} ici. Si l'utilisateur en choisit un (à l'oral), signalez-le avec humour et redemandez.

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
    ),
    "en": Templates(
        favorites="""It is now question {q_num} of {total}.

Question (id={qid}): "{question}"
Available choices: {choices}

FIRST action (before speaking): call notify_asking_top_2(question_id={qid}) to signal the interface that the cards are now clickable.

STEP: Then, in ONE natural sentence, ask {first_name} for {ask}. Do NOT enumerate the choices aloud — the user can see them on screen. The user may answer by speaking OR by clicking the cards on screen — if they click, you will be notified automatically and should NOT call notify_top_2 yourself in that case.

Once the user answers ORALLY (if they click instead, skip this — you'll be notified):
1. Match each spoken answer to the closest canonical label from: [{choices}]. Use semantic and phonetic understanding — the user may mispronounce, abbreviate, or give a partial answer (e.g. "delhi" → "Delhi", "jazz" → "Jazz et new age", "rock" → "Rock"). NEVER ask for clarification for ambiguous answers — pick the closest match and move on silently.
2. Call notify_top_2(question_id={qid}, top_2={example}) IMMEDIATELY.
3. Your mission for this step is complete.""",
        least="""Ask the user for {ask} from the REMAINING choices (excluding: {positives}). The user may answer by speaking OR by clicking the cards on screen — if they click, you will be notified automatically and should NOT call notify_bottom_2 yourself in that case.

IMPORTANT: Never accept one of {positives} here. If the user picks one (orally), point it out with humor and ask again.

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
    ),
    "es": Templates(
        favorites="""Esta es ahora la pregunta {q_num} de {total}.

Pregunta (id={qid}): "{question}"
Opciones disponibles: {choices}

PRIMERA acción (antes de hablar): llame a notify_asking_top_2(question_id={qid}) para indicar a la interfaz que las tarjetas ya son clicables.

PASO: Luego, en UNA sola frase natural, pregunte a {first_name} {ask}. NO enumere las opciones en voz alta — el usuario las ve en pantalla. El usuario puede responder DE VIVA VOZ o HACIENDO CLIC en las tarjetas en pantalla — si hace clic, se le notificará automáticamente y en ese caso NO debe llamar a notify_top_2 usted mismo/a.

Una vez que el usuario responda DE VIVA VOZ (si hace clic en su lugar, omita esto — se le notificará):
1. Haga corresponder cada respuesta oral con la etiqueta canónica más cercana entre: [{choices}]. Use su comprensión semántica y fonética — el usuario puede pronunciar mal, abreviar o dar una respuesta parcial. PROHIBIDO ABSOLUTO: nunca señale, corrija ni comente — elija la etiqueta más cercana y continúe directamente.
2. Llame INMEDIATAMENTE a notify_top_2(question_id={qid}, top_2={example}).
3. Su misión ha terminado.""",
        least="""Pida al usuario {ask} entre las opciones RESTANTES (excluyendo: {positives}). El usuario puede responder DE VIVA VOZ o HACIENDO CLIC en las tarjetas en pantalla — si hace clic, se le notificará automáticamente y en ese caso NO debe llamar a notify_bottom_2 usted mismo/a.

IMPORTANTE: Nunca acepte una de {positives} aquí. Si el usuario elige una (de viva voz), señálelo con humor y vuelva a preguntar.

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
    ),
    "de": Templates(
        favorites="""Dies ist nun Frage {q_num} von {total}.

Frage (id={qid}): "{question}"
Verfügbare Optionen: {choices}

ERSTE Aktion (bevor du sprichst): rufe notify_asking_top_2(question_id={qid}) auf, um der Oberfläche zu signalisieren, dass die Karten jetzt klickbar sind.

SCHRITT: Frage {first_name} dann in EINEM natürlichen Satz nach {ask}. Zähle die Optionen NIEMALS laut auf — der Nutzer sieht sie auf dem Bildschirm. Der Nutzer kann mündlich ODER durch Klicken auf die Karten antworten — klickt er, wirst du automatisch benachrichtigt und darfst notify_top_2 in diesem Fall NICHT selbst aufrufen.

Sobald der Nutzer MÜNDLICH antwortet (klickt er stattdessen, überspringe dies — du wirst benachrichtigt):
1. Ordne jede gesprochene Antwort dem nächstliegenden kanonischen Label zu aus: [{choices}]. Nutze semantisches und phonetisches Verständnis — der Nutzer kann falsch aussprechen, abkürzen oder unvollständig antworten. Frage NIEMALS bei mehrdeutigen Antworten nach — wähle die nächstliegende Übereinstimmung und mache direkt weiter.
2. Rufe SOFORT notify_top_2(question_id={qid}, top_2={example}) auf.
3. Deine Aufgabe für diesen Schritt ist abgeschlossen.""",
        least="""Frage den Nutzer nach {ask} aus den VERBLEIBENDEN Optionen (ausgeschlossen: {positives}). Der Nutzer kann mündlich ODER durch Klicken auf die Karten antworten — klickt er, wirst du automatisch benachrichtigt und darfst notify_bottom_2 in diesem Fall NICHT selbst aufrufen.

WICHTIG: Akzeptiere hier NIEMALS eine der Optionen {positives}. Wählt der Nutzer (mündlich) trotzdem eine davon, weise humorvoll darauf hin und frage erneut.

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
    ),
    "ar": Templates(
        favorites="""هذا هو الآن السؤال {q_num} من {total}.

السؤال (id={qid}): "{question}"
الخيارات المتاحة: {choices}

الإجراء الأول (قبل الكلام): استدعِ notify_asking_top_2(question_id={qid}) لإعلام الواجهة بأن البطاقات أصبحت قابلة للنقر.

الخطوة: ثم، في جملة طبيعية واحدة، اسأل {first_name} عن {ask}. لا تعدد الخيارات بصوت عالٍ — المستخدم يراها على الشاشة. يمكن للمستخدم الإجابة شفهيًا أو بالنقر على البطاقات على الشاشة — إذا نقر، سيتم إعلامك تلقائيًا ويجب ألا تستدعي notify_top_2 بنفسك في هذه الحالة.

بمجرد أن يجيب المستخدم شفهيًا (إذا نقر بدلاً من ذلك، تجاوز هذا — سيتم إعلامك):
1. طابق كل إجابة منطوقة مع التسمية القياسية الأقرب من: [{choices}]. استخدم فهمك الدلالي والصوتي — قد يخطئ المستخدم في النطق أو يختصر أو يعطي إجابة جزئية. لا تطلب أبدًا توضيحًا للإجابات الغامضة — اختر الأقرب تطابقًا وتابع بصمت.
2. استدعِ فورًا notify_top_2(question_id={qid}, top_2={example}).
3. مهمتك لهذه الخطوة اكتملت.""",
        least="""اطلب من المستخدم {ask} من بين الخيارات المتبقية (باستثناء: {positives}). يمكن للمستخدم الإجابة شفهيًا أو بالنقر على البطاقات على الشاشة — إذا نقر، سيتم إعلامك تلقائيًا ويجب ألا تستدعي notify_bottom_2 بنفسك في هذه الحالة.

مهم: لا تقبل أبدًا أحد الخيارات {positives} هنا. إذا اختار المستخدم أحدها (شفهيًا)، أشر إلى ذلك بروح الفكاهة واطلب مجددًا.

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
    ),
    "ru": Templates(
        favorites="""Сейчас вопрос {q_num} из {total}.

Вопрос (id={qid}): "{question}"
Доступные варианты: {choices}

ПЕРВОЕ действие (перед тем как говорить): вызови notify_asking_top_2(question_id={qid}), чтобы сообщить интерфейсу, что карточки теперь кликабельны.

ШАГ: Затем, в ОДНОМ естественном предложении, спроси {first_name} про {ask}. НЕ перечисляй варианты вслух — пользователь видит их на экране. Пользователь может ответить устно ИЛИ нажав на карточки на экране — если он нажмёт, тебя автоматически уведомят, и в этом случае ты НЕ должен сам вызывать notify_top_2.

Как только пользователь ответит УСТНО (если он нажмёт вместо этого, пропусти это — тебя уведомят):
1. Сопоставь каждый устный ответ с ближайшей канонической меткой из: [{choices}]. Используй семантическое и фонетическое понимание — пользователь может неправильно произнести, сократить или дать неполный ответ. НИКОГДА не проси уточнения при неоднозначных ответах — выбери ближайшее совпадение и продолжай молча.
2. СРАЗУ вызови notify_top_2(question_id={qid}, top_2={example}).
3. Твоя задача на этом шаге выполнена.""",
        least="""Попроси пользователя назвать {ask} из ОСТАВШИХСЯ вариантов (исключая: {positives}). Пользователь может ответить устно ИЛИ нажав на карточки на экране — если он нажмёт, тебя автоматически уведомят, и в этом случае ты НЕ должен сам вызывать notify_bottom_2.

ВАЖНО: Никогда не принимай здесь один из {positives}. Если пользователь выберет один из них (устно), укажи на это с юмором и спроси снова.

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
    ),
}


# ── Construction ─────────────────────────────────────────────────────────

def _parts(ctx: PromptContext) -> tuple[Templates, Wording, dict]:
    lang = ctx.lang if ctx.lang in TEMPLATES else "fr"
    fmt = answer_format(ctx.config)
    tpl, words = TEMPLATES[lang], WORDING[fmt.framing][lang]
    q = ctx.questions[ctx.state.current_question_index]
    choices = ", ".join(c["label"] if isinstance(c, dict) else c for c in q.get("choices", []))
    base = {
        "qid": q["id"],
        "question": q["question"],
        "choices": choices,
        "q_num": ctx.state.current_question_index + 1,
        "total": ctx.num_questions,
        "first_name": ctx.state.profile.get("first_name", ""),
        "fmt": fmt,
    }
    return tpl, words, base


def _example(tpl: Templates, n: int) -> str:
    return "[" + ", ".join(f"{tpl.choice_word}{i + 1}" for i in range(n)) + "]"


def _items(tpl: Templates, items: list[str]) -> str:
    items = items or ["?"]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + tpl.conj + items[-1]


def _current(items: list[str], index: int) -> str:
    return items[index] if index < len(items) else "?"


def q_favorites(ctx: PromptContext) -> str:
    tpl, words, b = _parts(ctx)
    n = b["fmt"].positive_count
    return tpl.favorites.format(**b, ask=words.ask_positive(n), example=_example(tpl, n))


def q_least(ctx: PromptContext) -> str:
    tpl, words, b = _parts(ctx)
    n = b["fmt"].negative_count
    return tpl.least.format(
        **b, ask=words.ask_negative(n), example=_example(tpl, n), positives=ctx.state.current_top_2,
    )


def q_justify_positive(ctx: PromptContext) -> str:
    tpl, words, b = _parts(ctx)
    choice = _current(ctx.state.current_top_2, ctx.state.justify_index)
    return tpl.justify_positive.format(**b, why=words.why_positive.format(choice=choice))


def q_justify_negative(ctx: PromptContext) -> str:
    tpl, words, b = _parts(ctx)
    choice = _current(ctx.state.current_bottom_2, ctx.state.justify_index)
    return tpl.justify_negative.format(**b, why=words.why_negative.format(choice=choice))


def q_confirm(ctx: PromptContext) -> str:
    tpl, words, b = _parts(ctx)
    top, bottom = ctx.state.current_top_2, ctx.state.current_bottom_2
    recap = words.recap_positive.format(items=_items(tpl, top))
    if b["fmt"].negative_count > 0:
        recap += ", " + words.recap_negative.format(items=_items(tpl, bottom))
    return tpl.confirm.format(**b, recap=recap, top=top, bottom=bottom)


MISSIONS = {
    AgentPhase.Q_FAVORITES: q_favorites,
    AgentPhase.Q_JUSTIFY_POSITIVE: q_justify_positive,
    AgentPhase.Q_LEAST: q_least,
    AgentPhase.Q_JUSTIFY_NEGATIVE: q_justify_negative,
    AgentPhase.Q_CONFIRM: q_confirm,
}
