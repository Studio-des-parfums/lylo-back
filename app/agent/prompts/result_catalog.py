"""Phases 3-4 — résultat « catalogue » (Ester) : 2 parfums existants du catalogue.

Textes déplacés tels quels depuis agent.py (get_prompt) — vérifiés par scripts/prompt_snapshot.py.
"""
from app.agent.prompts.context import PromptContext
from app.agent.state import AgentPhase


def intensity(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"""FIRST action (before speaking): call notify_asking_intensity(). Then in ONE short reply, tell {first_name} you're now going to find the perfumes from the catalog that best match their preferences. Immediately call generate_catalog_matches() — no question needed here."""
    elif lang == "es":
        mission = f"""PRIMERA acción (antes de hablar): llame a notify_asking_intensity(). Luego, en UNA sola réplica corta, anuncie a {first_name} que va a buscar ahora los perfumes del catálogo que mejor se ajustan a sus preferencias. Llame INMEDIATAMENTE a generate_catalog_matches() — no hace falta ninguna pregunta aquí."""
    elif lang == "de":
        mission = f"""ERSTE Aktion (bevor du sprichst): rufe notify_asking_intensity() auf. Teile {first_name} dann in EINER kurzen Antwort mit, dass du nun die Parfums aus dem Katalog suchst, die am besten zu den Präferenzen passen. Rufe SOFORT generate_catalog_matches() auf — hier ist keine Frage nötig."""
    elif lang == "ar":
        mission = f"""الإجراء الأول (قبل الكلام): استدعِ notify_asking_intensity(). ثم في رد قصير واحد، أخبر {first_name} بأنك ستبحث الآن عن العطور من الكتالوج التي تناسب تفضيلاته بشكل أفضل. استدعِ فورًا generate_catalog_matches() — لا حاجة لأي سؤال هنا."""
    elif lang == "ru":
        mission = f"""ПЕРВОЕ действие (перед тем как говорить): вызови notify_asking_intensity(). Затем в ОДНОМ коротком ответе скажи {first_name}, что ты сейчас найдёшь парфюмы из каталога, которые лучше всего соответствуют его(её) предпочтениям. СРАЗУ вызови generate_catalog_matches() — вопрос здесь не нужен."""
    else:
        mission = f"""PREMIÈRE action (avant de parler) : appelez notify_asking_intensity(). Puis en UNE SEULE réplique courte, annoncez à {first_name} que vous allez maintenant trouver les parfums du catalogue qui correspondent le mieux à ses préférences. Appelez IMMÉDIATEMENT generate_catalog_matches() — aucune question nécessaire ici."""
    return mission


def present_formulas(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"""Present the matched perfumes to {first_name} with enthusiasm. For each one:
1. The brand and perfume name (e.g. "The first one is Santal 33 by Le Labo")
2. A short atmospheric description based on its match reason — do NOT enumerate notes one by one unless asked

Then ask which one they prefer. Once the user clearly chooses one, call IMMEDIATELY select_formula(formula_index=N) matching their choice (0 for the first, 1 for the second, 2 for the third if there is one)."""
    elif lang == "es":
        mission = f"""Presente los perfumes seleccionados a {first_name} con entusiasmo. Para cada uno:
1. La marca y el nombre del perfume (ej: "El primero es Santal 33 de Le Labo")
2. Una breve descripción atmosférica basada en el motivo de su selección — NO enumere las notas una por una salvo que se lo pidan

Luego pregunte cuál prefiere. En cuanto el usuario elija claramente uno, llame INMEDIATAMENTE a select_formula(formula_index=N) según su elección (0 para el primero, 1 para el segundo, 2 para el tercero si lo hay)."""
    elif lang == "de":
        mission = f"""Präsentiere die gefundenen Parfums {first_name} mit Begeisterung. Für jedes:
1. Marke und Parfumname (z. B. "Das erste ist Santal 33 von Le Labo")
2. Eine kurze atmosphärische Beschreibung basierend auf dem Match-Grund — zähle die Noten NICHT einzeln auf, außer auf Nachfrage

Frage dann, welches bevorzugt wird. Sobald der Nutzer sich eindeutig entscheidet, rufe SOFORT select_formula(formula_index=N) entsprechend der Wahl auf (0 für das erste, 1 für das zweite, 2 für das dritte, falls vorhanden)."""
    elif lang == "ar":
        mission = f"""قدّم العطور المطابقة إلى {first_name} بحماس. لكل واحد:
1. العلامة التجارية واسم العطر (مثال: "الأول هو Santal 33 من Le Labo")
2. وصف جوي قصير مبني على سبب التطابق — لا تعدد النوتات واحدة تلو الأخرى إلا إذا طُلب منك ذلك

ثم اسأل عن العطر المفضل. بمجرد أن يختار المستخدم بوضوح، استدعِ فورًا select_formula(formula_index=N) وفقًا لاختياره (0 للأول، 1 للثاني، 2 للثالث إن وجد)."""
    elif lang == "ru":
        mission = f"""Представь подобранные парфюмы {first_name} с энтузиазмом. Для каждого:
1. Бренд и название парфюма (например, "Первый — это Santal 33 от Le Labo")
2. Короткое атмосферное описание на основе причины совпадения — НЕ перечисляй ноты одну за другой, если не спросят

Затем спроси, какой из них предпочтителен. Как только пользователь чётко выберет один, СРАЗУ вызови select_formula(formula_index=N) в соответствии с его выбором (0 для первого, 1 для второго, 2 для третьего, если есть)."""
    else:
        mission = f"""Présentez les parfums sélectionnés à {first_name} avec enthousiasme. Pour chacun :
1. La marque et le nom du parfum (ex : "Le premier est Santal 33 de Le Labo")
2. Une courte description atmosphérique basée sur la raison de sa sélection — ne listez PAS les notes une par une sauf si demandé

Demandez ensuite lequel l'utilisateur préfère. Dès qu'il/elle choisit clairement, appelez IMMÉDIATEMENT select_formula(formula_index=N) correspondant à son choix (0 pour le premier, 1 pour le deuxième, 2 pour le troisième s'il y en a un)."""
    return mission


def customization(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")

    if is_en:
        mission = f"""You are now discussing the selected perfume with {first_name}. Talk about it with enthusiasm — its brand, character, what makes it unique, its olfactory atmosphere. Answer any questions about it as a perfumery expert. This is a real commercial perfume, not a custom formula — there is no note replacement or intensity change available.

**Transition to standby:** Once the user is satisfied, ask "Any more questions about your perfume?" If no more questions, say ONE short farewell sentence then IMMEDIATELY call enter_pause_mode(). Do NOT mention any wake phrase. If the user says "thank you", "goodbye", or anything similar after your farewell — call enter_pause_mode() immediately without saying anything more."""
    elif lang == "es":
        mission = f"""Ahora está hablando del perfume seleccionado con {first_name}. Hable de él con entusiasmo — su marca, carácter, lo que lo hace único, su ambiente olfativo. Responda a cualquier pregunta al respecto como experto/a en perfumería. Es un perfume comercial real, no una fórmula a medida — no hay reemplazo de notas ni cambio de intensidad disponible.

**Transición a la espera:** Una vez que el usuario esté satisfecho, pregunte "¿Alguna otra pregunta sobre su perfume?" Si no hay más preguntas, diga UNA breve frase de despedida y luego llame INMEDIATAMENTE a enter_pause_mode(). No mencione ninguna frase de activación por voz. Si el usuario dice "gracias", "adiós" o algo similar después de su despedida — llame a enter_pause_mode() inmediatamente sin decir nada más."""
    elif lang == "de":
        mission = f"""Du sprichst nun mit {first_name} über das ausgewählte Parfum. Sprich mit Begeisterung darüber — Marke, Charakter, was es einzigartig macht, seine olfaktorische Atmosphäre. Beantworte jede Frage dazu als Parfümerie-Experte. Dies ist ein echtes kommerzielles Parfum, keine individuelle Formel — es gibt keinen Notenaustausch oder keine Intensitätsänderung.

**Übergang in den Standby:** Sobald der Nutzer zufrieden ist, frage "Haben Sie noch weitere Fragen zu Ihrem Parfum?" Gibt es keine weiteren Fragen, sage EINEN kurzen Abschiedssatz und rufe dann SOFORT enter_pause_mode() auf. Erwähne KEINE Weckphrase. Sagt der Nutzer nach deinem Abschied "danke", "auf Wiedersehen" oder Ähnliches — rufe sofort enter_pause_mode() auf, ohne noch etwas zu sagen."""
    elif lang == "ar":
        mission = f"""أنت الآن تتحدث مع {first_name} عن العطر المختار. تحدث عنه بحماس — علامته التجارية، شخصيته، ما يجعله فريدًا، أجواءه العطرية. أجب عن أي سؤال حوله كخبير عطور. هذا عطر تجاري حقيقي، وليس تركيبة مخصصة — لا يوجد استبدال للنوتات أو تغيير للشدة.

**الانتقال إلى وضع الاستعداد:** بمجرد أن يرضى المستخدم، اسأل "هل لديك أسئلة أخرى عن عطرك؟" إذا لم تكن هناك أسئلة أخرى، قل جملة وداع قصيرة واحدة ثم استدعِ فورًا enter_pause_mode(). لا تذكر أي عبارة تنشيط صوتي. إذا قال المستخدم "شكرًا" أو "وداعًا" أو ما شابه بعد وداعك — استدعِ enter_pause_mode() فورًا دون قول أي شيء آخر."""
    elif lang == "ru":
        mission = f"""Ты сейчас обсуждаешь с {first_name} выбранный парфюм. Говори о нём с энтузиазмом — бренд, характер, что делает его уникальным, его ольфакторная атмосфера. Отвечай на любые вопросы как эксперт по парфюмерии. Это настоящий коммерческий парфюм, а не индивидуальная формула — замена нот или изменение интенсивности недоступны.

**Переход в режим ожидания:** Как только пользователь удовлетворён, спроси "Есть ли у вас ещё вопросы о вашем парфюме?" Если вопросов больше нет, скажи ОДНО короткое прощальное предложение и СРАЗУ вызови enter_pause_mode(). НЕ упоминай фразу пробуждения. Если пользователь скажет "спасибо", "до свидания" или что-то подобное после твоего прощания — сразу вызови enter_pause_mode(), больше ничего не говоря."""
    else:
        mission = f"""Vous discutez maintenant du parfum sélectionné avec {first_name}. Parlez-en avec enthousiasme — sa marque, son caractère, ce qui le rend unique, son ambiance olfactive. Répondez à toute question à ce sujet en tant qu'expert en parfumerie. C'est un vrai parfum du commerce, pas une formule sur-mesure — aucun remplacement de note ni changement d'intensité n'est disponible.

**Transition vers la veille :** Une fois l'utilisateur satisfait, demandez "Avez-vous d'autres questions sur votre parfum ?" Si plus de questions, dites UNE courte phrase d'au revoir puis appelez IMMÉDIATEMENT enter_pause_mode(). Ne mentionnez AUCUNE phrase de réveil vocal. Si l'utilisateur dit "merci", "au revoir" ou quoi que ce soit après votre au revoir — appelez enter_pause_mode() immédiatement sans rien dire de plus."""
    return mission


MISSIONS = {
    AgentPhase.INTENSITY: intensity,
    AgentPhase.PRESENT_FORMULAS: present_formulas,
    AgentPhase.CUSTOMIZATION: customization,
}
