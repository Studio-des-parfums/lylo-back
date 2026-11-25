"""Phase 1 — profil et questions de sécurité (communes à toutes les marques).

Textes déplacés tels quels depuis agent.py (get_prompt) — vérifiés par scripts/prompt_snapshot.py.
"""
from app.agent.prompts.context import PromptContext
from app.agent.state import AgentPhase


def greet(ctx: PromptContext) -> str:
    lang, is_en, ai_name = ctx.lang, ctx.is_en, ctx.ai_name
    if is_en:
        mission = f"Greet the user warmly and simply. Introduce yourself just with your first name ({ai_name}). For example: 'Hey! I'm {ai_name}, nice to meet you! And what's your name?' Be natural and friendly. As soon as the user gives their name, call save_user_profile(field='first_name', value=<their name>) IMMEDIATELY."
    elif lang == "es":
        mission = f"Salude al usuario cálidamente y con sencillez, tratándolo de usted. Preséntese solo con su nombre ({ai_name}). Por ejemplo: '¡Hola! Soy {ai_name}, ¡encantada de conocerle! ¿Y usted, cómo se llama?' Sea natural y amable. En cuanto el usuario dé su nombre, llame INMEDIATAMENTE a save_user_profile(field='first_name', value=<el nombre>)."
    elif lang == "de":
        mission = f"Begrüße den Nutzer herzlich und einfach, und sieze ihn dabei. Stelle dich nur mit deinem Vornamen vor ({ai_name}). Zum Beispiel: 'Hallo! Ich bin {ai_name}, schön Sie kennenzulernen! Und wie heißen Sie?' Sei natürlich und freundlich. Sobald der Nutzer seinen Vornamen nennt, rufe SOFORT save_user_profile(field='first_name', value=<der Vorname>) auf."
    elif lang == "ar":
        mission = f"رحّب بالمستخدم بحرارة وبساطة، مخاطبًا إياه بصيغة الاحترام. قدّم نفسك فقط باسمك الأول ({ai_name}). على سبيل المثال: 'مرحبًا! أنا {ai_name}، تشرفت بمعرفتك! وما اسمك أنت؟' كن طبيعيًا وودودًا. بمجرد أن يعطي المستخدم اسمه، استدعِ فورًا save_user_profile(field='first_name', value=<الاسم>)."
    elif lang == "ru":
        mission = f"Поприветствуй пользователя тепло и просто, на \"вы\". Представься только своим именем ({ai_name}). Например: 'Привет! Меня зовут {ai_name}, приятно познакомиться! А как вас зовут?' Будь естественным(ой) и дружелюбным(ой). Как только пользователь назовёт имя, СРАЗУ вызови save_user_profile(field='first_name', value=<имя>)."
    else:
        mission = f"Saluez l'utilisateur chaleureusement et simplement en le vouvoyant. Présentez-vous juste avec votre prénom ({ai_name}). Par exemple : 'Bonjour ! Moi c'est {ai_name}, enchantée ! Et vous, comment vous appelez-vous ?' Soyez naturel(le). Dès que l'utilisateur donne son prénom, appelez IMMÉDIATEMENT save_user_profile(field='first_name', value=<le prénom>)."
    return mission


def get_gender(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"The user's name is {first_name}. Ask naturally whether it's a masculine or feminine name, for example: 'Nice name! Is it more of a masculine or feminine name?' As soon as they answer, IMMEDIATELY call save_user_profile(field='gender', value='masculin') or save_user_profile(field='gender', value='féminin')."
    elif lang == "es":
        mission = f"El nombre del usuario es {first_name}. Pregunte con naturalidad si es un nombre masculino o femenino, por ejemplo: '¡Bonito nombre! ¿Es más bien masculino o femenino?' En cuanto responda, llame INMEDIATAMENTE a save_user_profile(field='gender', value='masculin') o save_user_profile(field='gender', value='féminin')."
    elif lang == "de":
        mission = f"Der Vorname des Nutzers ist {first_name}. Frage natürlich, ob es sich um einen männlichen oder weiblichen Namen handelt, zum Beispiel: 'Schöner Name! Ist das eher ein männlicher oder weiblicher Name?' Sobald er antwortet, rufe SOFORT save_user_profile(field='gender', value='masculin') oder save_user_profile(field='gender', value='féminin') auf."
    elif lang == "ar":
        mission = f"اسم المستخدم هو {first_name}. اسأل بشكل طبيعي عما إذا كان الاسم مذكرًا أم مؤنثًا، على سبيل المثال: 'اسم جميل! هل هو أقرب إلى المذكر أم المؤنث؟' بمجرد أن يجيب، استدعِ فورًا save_user_profile(field='gender', value='masculin') أو save_user_profile(field='gender', value='féminin')."
    elif lang == "ru":
        mission = f"Имя пользователя {first_name}. Естественно спроси, мужское это имя или женское, например: 'Красивое имя! Это скорее мужское или женское имя?' Как только он(а) ответит, СРАЗУ вызови save_user_profile(field='gender', value='masculin') или save_user_profile(field='gender', value='féminin')."
    else:
        mission = f"Le prénom de l'utilisateur est {first_name}. Demandez naturellement si c'est un prénom masculin ou féminin, par exemple : 'Joli prénom ! C'est plutôt masculin ou féminin ?' Dès qu'il/elle répond, appelez IMMÉDIATEMENT save_user_profile(field='gender', value='masculin') ou save_user_profile(field='gender', value='féminin')."
    mission += (
        "\n\nThis step is REQUIRED: the perfume recommendation is completely different for a masculine or a "
        "feminine profile. Only masculine or feminine can be recorded. If the user answers anything else "
        "(neither, prefers not to say, off-topic), kindly explain why you need it and ask again; never move on "
        "without it. If the answer contains extra words (\"c'est bien, masculin\"), extract the gender."
    )
    return mission


def get_age(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"Ask {first_name} their age casually, for example: 'And how old are you?' IMPORTANT: Accept numbers written in words (e.g. 'twenty-five' → 25). Valid range: 12–120. If absurd, use humor. As soon as they give a valid age, IMMEDIATELY call save_user_profile(field='age', value=<age as number>)."
    elif lang == "es":
        mission = f"Pregunte la edad de {first_name} con naturalidad, por ejemplo: '¿Y cuántos años tiene?' IMPORTANTE: Acepte números escritos en letras (ej: 'veinticinco' → 25). Rango válido: 12–120 años. Si la edad es absurda, use el humor. En cuanto dé una edad válida, llame INMEDIATAMENTE a save_user_profile(field='age', value=<edad en número>)."
    elif lang == "de":
        mission = f"Frage {first_name} beiläufig nach dem Alter, zum Beispiel: 'Und wie alt sind Sie?' WICHTIG: Akzeptiere in Worten geschriebene Zahlen (z. B. 'fünfundzwanzig' → 25). Gültiger Bereich: 12–120. Bei absurden Angaben nutze Humor. Sobald ein gültiges Alter genannt wird, rufe SOFORT save_user_profile(field='age', value=<Alter als Zahl>) auf."
    elif lang == "ar":
        mission = f"اسأل {first_name} عن عمره بخفة، على سبيل المثال: 'وكم عمرك؟' مهم: اقبل الأرقام المكتوبة بالحروف (مثال: 'خمسة وعشرون' → 25). النطاق الصالح: 12–120 سنة. إذا كان العمر غير منطقي، استخدم الفكاهة. بمجرد إعطاء عمر صالح، استدعِ فورًا save_user_profile(field='age', value=<العمر كرقم>)."
    elif lang == "ru":
        mission = f"Непринуждённо спроси {first_name} о возрасте, например: 'А сколько вам лет?' ВАЖНО: Принимай числа, написанные словами (например, 'двадцать пять' → 25). Допустимый диапазон: 12–120. Если возраст абсурден, используй юмор. Как только будет назван допустимый возраст, СРАЗУ вызови save_user_profile(field='age', value=<возраст числом>)."
    else:
        mission = f"Demandez l'âge de {first_name} avec légèreté, par exemple : 'Et vous avez quel âge ?' IMPORTANT : Acceptez les nombres écrits en lettres (ex : 'vingt-cinq' → 25). Plage valide : 12–120 ans. Si l'âge est absurde, utilisez l'humour. Dès qu'il/elle donne un âge valide, appelez IMMÉDIATEMENT save_user_profile(field='age', value=<âge en chiffre>)."
    return mission


def get_pregnant(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"Ask {first_name} naturally and delicately whether she is pregnant or breastfeeding, as some fragrance ingredients require precautions. For example: 'Just to make sure we create the safest formula for you — are you currently pregnant or breastfeeding?' As soon as she answers, IMMEDIATELY call save_user_profile(field='pregnant', value='oui') or save_user_profile(field='pregnant', value='non')."
    elif lang == "es":
        mission = f"Pregunte a {first_name} con naturalidad y delicadeza si está embarazada o en periodo de lactancia, ya que algunos ingredientes requieren precauciones. Por ejemplo: 'Para garantizarle la fórmula más segura, ¿está usted actualmente embarazada o en periodo de lactancia?' En cuanto responda, llame INMEDIATAMENTE a save_user_profile(field='pregnant', value='oui') o save_user_profile(field='pregnant', value='non')."
    elif lang == "de":
        mission = f"Frage {first_name} natürlich und einfühlsam, ob sie schwanger ist oder stillt, da manche Duftstoffe Vorsichtsmaßnahmen erfordern. Zum Beispiel: 'Damit wir Ihnen die sicherste Formel zusammenstellen können — sind Sie aktuell schwanger oder stillen Sie?' Sobald sie antwortet, rufe SOFORT save_user_profile(field='pregnant', value='oui') oder save_user_profile(field='pregnant', value='non') auf."
    elif lang == "ar":
        mission = f"اسأل {first_name} بشكل طبيعي ولطيف عما إذا كانت حاملاً أو مرضعة، لأن بعض مكونات العطور تتطلب احتياطات. على سبيل المثال: 'لضمان أفضل تركيبة آمنة لك — هل أنتِ حالياً حامل أو مرضعة؟' بمجرد أن تجيب، استدعِ فورًا save_user_profile(field='pregnant', value='oui') أو save_user_profile(field='pregnant', value='non')."
    elif lang == "ru":
        mission = f"Естественно и деликатно спроси {first_name}, не беременна ли она или не кормит ли грудью, так как некоторые ароматические ингредиенты требуют предосторожности. Например: 'Чтобы гарантировать вам самую безопасную формулу — вы сейчас беременны или кормите грудью?' Как только она ответит, СРАЗУ вызови save_user_profile(field='pregnant', value='oui') или save_user_profile(field='pregnant', value='non')."
    else:
        mission = f"Demandez à {first_name} naturellement et avec délicatesse si elle est enceinte ou allaitante, car certains ingrédients demandent des précautions. Par exemple : 'Pour vous garantir la formule la plus sûre — êtes-vous actuellement enceinte ou allaitante ?' Dès qu'elle répond, appelez IMMÉDIATEMENT save_user_profile(field='pregnant', value='oui') ou save_user_profile(field='pregnant', value='non')."
    return mission


def get_dislikes(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"Ask {first_name} naturally if there are any notes or scents they dislike and would prefer to avoid, for example: 'Is there any particular note or scent you don't like, that we should avoid?' — If NO: IMMEDIATELY call save_user_profile(field='has_disliked_notes', value='non'). — If YES: IMMEDIATELY call save_user_profile(field='has_disliked_notes', value='oui')."
    elif lang == "es":
        mission = f"Pregunte a {first_name} con naturalidad si hay alguna nota u olor que no le guste y que prefiera evitar, por ejemplo: '¿Hay alguna nota u olor en particular que no le guste, que debamos evitar?' — Si NO: llame INMEDIATAMENTE a save_user_profile(field='has_disliked_notes', value='non'). — Si SÍ: llame INMEDIATAMENTE a save_user_profile(field='has_disliked_notes', value='oui')."
    elif lang == "de":
        mission = f"Frage {first_name} natürlich, ob es bestimmte Noten oder Düfte gibt, die nicht gefallen und vermieden werden sollten, zum Beispiel: 'Gibt es eine bestimmte Note oder einen Duft, den Sie nicht mögen und den wir vermeiden sollten?' — Falls NEIN: rufe SOFORT save_user_profile(field='has_disliked_notes', value='non') auf. — Falls JA: rufe SOFORT save_user_profile(field='has_disliked_notes', value='oui') auf."
    elif lang == "ar":
        mission = f"اسأل {first_name} بشكل طبيعي عما إذا كانت هناك رائحة أو نفحة معينة لا يحبها ويفضل تجنبها، على سبيل المثال: 'هل هناك نفحة أو رائحة معينة لا تحبها ونحتاج إلى تجنبها؟' — إذا كانت الإجابة لا: استدعِ فورًا save_user_profile(field='has_disliked_notes', value='non'). — إذا كانت الإجابة نعم: استدعِ فورًا save_user_profile(field='has_disliked_notes', value='oui')."
    elif lang == "ru":
        mission = f"Естественно спроси {first_name}, есть ли какая-то нота или запах, который он(а) не любит и который лучше избегать, например: 'Есть ли какая-то конкретная нота или запах, который вам не нравится и который нам следует избегать?' — Если НЕТ: СРАЗУ вызови save_user_profile(field='has_disliked_notes', value='non'). — Если ДА: СРАЗУ вызови save_user_profile(field='has_disliked_notes', value='oui')."
    else:
        mission = f"Demandez à {first_name} naturellement s'il y a une note ou une odeur qu'il/elle n'aime pas et préférerait éviter, par exemple : 'Est-ce qu'il y a une note ou une odeur en particulier que vous n'aimez pas, qu'on devrait éviter ?' — Si NON : appelez IMMÉDIATEMENT save_user_profile(field='has_disliked_notes', value='non'). — Si OUI : appelez IMMÉDIATEMENT save_user_profile(field='has_disliked_notes', value='oui')."
    return mission


def get_dislike_detail(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"Ask {first_name} which notes or scents they dislike, for example: 'Noted! Which notes or scents should we avoid?' As soon as they answer, IMMEDIATELY call save_user_profile(field='disliked_notes', value=<the notes mentioned>)."
    elif lang == "es":
        mission = f"Pregunte a {first_name} qué notas u olores no le gustan, por ejemplo: '¡Entendido! ¿Qué notas u olores debemos evitar?' En cuanto responda, llame INMEDIATAMENTE a save_user_profile(field='disliked_notes', value=<las notas mencionadas>)."
    elif lang == "de":
        mission = f"Frage {first_name}, welche Noten oder Düfte nicht gefallen, zum Beispiel: 'Verstanden! Welche Noten oder Düfte sollten wir vermeiden?' Sobald geantwortet wird, rufe SOFORT save_user_profile(field='disliked_notes', value=<die genannten Noten>) auf."
    elif lang == "ar":
        mission = f"اسأل {first_name} عن النفحات أو الروائح التي لا يحبها، على سبيل المثال: 'تمام! ما هي النفحات أو الروائح التي يجب أن نتجنبها؟' بمجرد أن يجيب، استدعِ فورًا save_user_profile(field='disliked_notes', value=<النفحات المذكورة>)."
    elif lang == "ru":
        mission = f"Спроси {first_name}, какие ноты или запахи ему(ей) не нравятся, например: 'Понятно! Какие ноты или запахи нам следует избегать?' Как только он(а) ответит, СРАЗУ вызови save_user_profile(field='disliked_notes', value=<указанные ноты>)."
    else:
        mission = f"Demandez à {first_name} quelles notes ou odeurs il/elle n'aime pas, par exemple : 'Entendu ! Quelles notes ou odeurs devrait-on éviter ?' Dès qu'il/elle répond, appelez IMMÉDIATEMENT save_user_profile(field='disliked_notes', value=<les notes mentionnées>)."
    return mission


def get_allergies(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"Ask {first_name} naturally if they have any allergies or sensitivities to certain ingredients, for example: 'Before we start, do you have any allergies or sensitivities to certain ingredients?' — If NO: IMMEDIATELY call save_user_profile(field='has_allergies', value='non'). — If YES: IMMEDIATELY call save_user_profile(field='has_allergies', value='oui')."
    elif lang == "es":
        mission = f"Pregunte a {first_name} con naturalidad si tiene alguna alergia o sensibilidad a ciertos ingredientes, por ejemplo: 'Antes de empezar, ¿tiene alguna alergia o sensibilidad a algún ingrediente?' — Si NO: llame INMEDIATAMENTE a save_user_profile(field='has_allergies', value='non'). — Si SÍ: llame INMEDIATAMENTE a save_user_profile(field='has_allergies', value='oui')."
    elif lang == "de":
        mission = f"Frage {first_name} natürlich, ob Allergien oder Empfindlichkeiten gegenüber bestimmten Inhaltsstoffen bestehen, zum Beispiel: 'Bevor wir beginnen — haben Sie Allergien oder Empfindlichkeiten gegenüber bestimmten Inhaltsstoffen?' — Falls NEIN: rufe SOFORT save_user_profile(field='has_allergies', value='non') auf. — Falls JA: rufe SOFORT save_user_profile(field='has_allergies', value='oui') auf."
    elif lang == "ar":
        mission = f"اسأل {first_name} بشكل طبيعي عما إذا كانت لديه أي حساسية أو حساسية تجاه مكونات معينة، على سبيل المثال: 'قبل أن نبدأ، هل لديك أي حساسية أو حساسية تجاه بعض المكونات؟' — إذا كانت الإجابة لا: استدعِ فورًا save_user_profile(field='has_allergies', value='non'). — إذا كانت الإجابة نعم: استدعِ فورًا save_user_profile(field='has_allergies', value='oui')."
    elif lang == "ru":
        mission = f"Естественно спроси {first_name}, есть ли у него(неё) аллергии или чувствительность к определённым ингредиентам, например: 'Прежде чем начать, у вас есть аллергии или чувствительность к каким-либо ингредиентам?' — Если НЕТ: СРАЗУ вызови save_user_profile(field='has_allergies', value='non'). — Если ДА: СРАЗУ вызови save_user_profile(field='has_allergies', value='oui')."
    else:
        mission = f"Demandez à {first_name} naturellement s'il/elle a des allergies ou sensibilités particulières, par exemple : 'Avant qu'on commence, est-ce que vous avez des allergies ou des sensibilités à certains ingrédients ?' — Si NON : appelez IMMÉDIATEMENT save_user_profile(field='has_allergies', value='non'). — Si OUI : appelez IMMÉDIATEMENT save_user_profile(field='has_allergies', value='oui')."
    return mission


def get_allergy_detail(ctx: PromptContext) -> str:
    lang, is_en, state = ctx.lang, ctx.is_en, ctx.state
    first_name = state.profile.get("first_name", "")
    if is_en:
        mission = f"Ask {first_name} which ingredients or substances they are allergic to, for example: 'Of course! Which ingredients or substances are you allergic to?' As soon as they answer, IMMEDIATELY call save_user_profile(field='allergies', value=<the allergies mentioned>)."
    elif lang == "es":
        mission = f"Pregunte a {first_name} a qué ingredientes o sustancias es alérgico/a, por ejemplo: '¡Claro! ¿A qué ingredientes o sustancias es usted alérgico/a?' En cuanto responda, llame INMEDIATAMENTE a save_user_profile(field='allergies', value=<las alergias mencionadas>)."
    elif lang == "de":
        mission = f"Frage {first_name}, gegen welche Inhaltsstoffe oder Substanzen eine Allergie besteht, zum Beispiel: 'Natürlich! Gegen welche Inhaltsstoffe oder Substanzen sind Sie allergisch?' Sobald geantwortet wird, rufe SOFORT save_user_profile(field='allergies', value=<die genannten Allergien>) auf."
    elif lang == "ar":
        mission = f"اسأل {first_name} عن المكونات أو المواد التي يعاني منها حساسية تجاهها، على سبيل المثال: 'بالطبع! ما هي المكونات أو المواد التي تعاني من حساسية تجاهها؟' بمجرد أن يجيب، استدعِ فورًا save_user_profile(field='allergies', value=<الحساسيات المذكورة>)."
    elif lang == "ru":
        mission = f"Спроси {first_name}, на какие ингредиенты или вещества у него(неё) аллергия, например: 'Конечно! На какие ингредиенты или вещества у вас аллергия?' Как только он(а) ответит, СРАЗУ вызови save_user_profile(field='allergies', value=<указанные аллергии>)."
    else:
        mission = f"Demandez à {first_name} à quels ingrédients ou substances il/elle est allergique, par exemple : 'Bien sûr ! À quels ingrédients ou substances êtes-vous allergique ?' Dès qu'il/elle répond, appelez IMMÉDIATEMENT save_user_profile(field='allergies', value=<les allergies mentionnées>)."
    return mission


MISSIONS = {
    AgentPhase.GREET: greet,
    AgentPhase.GET_GENDER: get_gender,
    AgentPhase.GET_AGE: get_age,
    AgentPhase.GET_PREGNANT: get_pregnant,
    AgentPhase.GET_DISLIKES: get_dislikes,
    AgentPhase.GET_DISLIKE_DETAIL: get_dislike_detail,
    AgentPhase.GET_ALLERGIES: get_allergies,
    AgentPhase.GET_ALLERGY_DETAIL: get_allergy_detail,
}
