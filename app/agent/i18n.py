"""Messages courts renvoyés au LLM (erreurs, accusés de réception), par langue."""
from app.core.languages import SupportedLanguage

# Petits messages utilitaires (erreurs, accusés de réception courts) renvoyés au LLM —
# pas de la prose de mission, donc pas besoin d'un dict par phase comme PERSONALITY/get_prompt.
TRANSLATIONS: dict[str, dict[SupportedLanguage, str]] = {
    "error": {"fr": "Erreur", "en": "Error", "es": "Error", "de": "Fehler", "ar": "خطأ", "ru": "Ошибка"},
    "cannot_save_answer": {
        "fr": "Erreur : impossible de sauvegarder dans l'état actuel.",
        "en": "Error: cannot save answer in current state.",
        "es": "Error: no se puede guardar la respuesta en el estado actual.",
        "de": "Fehler: Antwort kann im aktuellen Zustand nicht gespeichert werden.",
        "ar": "خطأ: لا يمكن حفظ الإجابة في الحالة الحالية.",
        "ru": "Ошибка: невозможно сохранить ответ в текущем состоянии.",
    },
    "unable_to_generate_formulas": {
        "fr": "Impossible de générer les formules",
        "en": "Unable to generate formulas",
        "es": "No se pudieron generar las fórmulas",
        "de": "Formeln konnten nicht generiert werden",
        "ar": "تعذر إنشاء التركيبات",
        "ru": "Не удалось создать формулы",
    },
    "unable_to_find_matches": {
        "fr": "Impossible de trouver des parfums correspondants",
        "en": "Unable to find matching perfumes",
        "es": "No se pudieron encontrar perfumes coincidentes",
        "de": "Es konnten keine passenden Parfums gefunden werden",
        "ar": "تعذر العثور على عطور مطابقة",
        "ru": "Не удалось найти подходящие парфюмы",
    },
    "profile_updated": {
        "fr": "Profil mis à jour : {field} = {value}",
        "en": "Profile updated: {field} = {value}",
        "es": "Perfil actualizado: {field} = {value}",
        "de": "Profil aktualisiert: {field} = {value}",
        "ar": "تم تحديث الملف الشخصي: {field} = {value}",
        "ru": "Профиль обновлён: {field} = {value}",
    },
    "frontend_notified_top_2": {
        "fr": "Frontend notifié : demande des 2 favoris.",
        "en": "Frontend notified: asking for top 2.",
        "es": "Frontend notificado: solicitando los 2 favoritos.",
        "de": "Frontend benachrichtigt: Abfrage der 2 Favoriten.",
        "ar": "تم إعلام الواجهة: طلب الخيارين المفضلين.",
        "ru": "Фронтенд уведомлён: запрос 2 любимых вариантов.",
    },
    "frontend_notified_intensity": {
        "fr": "Frontend notifié : demande de préférence d'intensité.",
        "en": "Frontend notified: asking intensity preference.",
        "es": "Frontend notificado: solicitando preferencia de intensidad.",
        "de": "Frontend benachrichtigt: Abfrage der Intensitätspräferenz.",
        "ar": "تم إعلام الواجهة: طلب تفضيل الشدة.",
        "ru": "Фронтенд уведомлён: запрос предпочтения интенсивности.",
    },
    "note_replaced": {
        "fr": "Note remplacée : {old_note} → {new_note}.",
        "en": "Note replaced: {old_note} → {new_note}.",
        "es": "Nota reemplazada: {old_note} → {new_note}.",
        "de": "Note ersetzt: {old_note} → {new_note}.",
        "ar": "تم استبدال النوتة: {old_note} → {new_note}.",
        "ru": "Нота заменена: {old_note} → {new_note}.",
    },
    "formula_type_changed": {
        "fr": "Type de formule changé en '{formula_type}'.",
        "en": "Formula type changed to '{formula_type}'.",
        "es": "Tipo de fórmula cambiado a '{formula_type}'.",
        "de": "Formeltyp geändert zu '{formula_type}'.",
        "ar": "تم تغيير نوع التركيبة إلى '{formula_type}'.",
        "ru": "Тип формулы изменён на '{formula_type}'.",
    },
    "standby_activated": {
        "fr": "Mode veille activé. Ne dis plus rien.",
        "en": "Standby mode activated. Do not say anything else.",
        "es": "Modo de espera activado. No digas nada más.",
        "de": "Standby-Modus aktiviert. Sag nichts mehr.",
        "ar": "تم تفعيل وضع الاستعداد. لا تقل شيئًا آخر.",
        "ru": "Режим ожидания активирован. Больше ничего не говори.",
    },
    "questionnaire_incomplete": {
        "fr": (
            "Erreur : le questionnaire n'est pas terminé "
            "({answered}/{total} questions répondues). "
            "C'est un choix personnel à l'utilisateur — vous ne pouvez pas décider ou "
            "recommander une réponse à sa place. N'appelez PAS generate_formulas. "
            "Expliquez-lui avec douceur que vous avez besoin de sa propre préférence pour "
            "créer une formule qui lui correspond, puis reprenez le questionnaire là où "
            "il en était."
        ),
        "en": (
            "Error: the questionnaire is not finished yet "
            "({answered}/{total} questions answered). "
            "This is a personal choice for the user to make — you cannot decide or "
            "recommend an answer on their behalf. Do NOT call generate_formulas. "
            "Instead, gently explain that you need their own preference to build a "
            "formula tailored to them, then continue the questionnaire from where it "
            "was left off."
        ),
        "es": (
            "Error: el cuestionario todavía no ha terminado "
            "({answered}/{total} preguntas respondidas). "
            "Esta es una decisión personal del usuario — no puede decidir ni "
            "recomendar una respuesta en su lugar. NO llame a generate_formulas. "
            "En su lugar, explíquele con delicadeza que necesita su propia preferencia "
            "para crear una fórmula a su medida, y luego retome el cuestionario donde "
            "se quedó."
        ),
        "de": (
            "Fehler: der Fragebogen ist noch nicht abgeschlossen "
            "({answered}/{total} Fragen beantwortet). "
            "Dies ist eine persönliche Entscheidung des Nutzers — du kannst nicht an "
            "seiner Stelle entscheiden oder eine Antwort empfehlen. Rufe NICHT "
            "generate_formulas auf. Erkläre stattdessen sanft, dass du seine eigene "
            "Präferenz brauchst, um eine passende Formel zu erstellen, und setze dann "
            "den Fragebogen dort fort, wo er unterbrochen wurde."
        ),
        "ar": (
            "خطأ: الاستبيان لم ينتهِ بعد "
            "({answered}/{total} أسئلة تمت الإجابة عليها). "
            "هذا قرار شخصي يعود للمستخدم — لا يمكنك أن تقرر أو "
            "توصي بإجابة نيابة عنه. لا تستدعِ generate_formulas. "
            "بدلاً من ذلك، اشرح له بلطف أنك بحاجة إلى تفضيله الشخصي "
            "لإنشاء تركيبة تناسبه، ثم تابع الاستبيان من حيث توقف."
        ),
        "ru": (
            "Ошибка: анкета ещё не завершена "
            "({answered}/{total} вопросов отвечено). "
            "Это личный выбор пользователя — ты не можешь решать или "
            "рекомендовать ответ вместо него. НЕ вызывай generate_formulas. "
            "Вместо этого мягко объясни, что тебе нужно его собственное "
            "предпочтение, чтобы создать подходящую формулу, затем продолжи "
            "анкету с того места, где она была прервана."
        ),
    },
    "inactivity_farewell": {
        "fr": "On dirait que vous vous êtes absenté(e) — je vais clore notre session. N'hésitez pas à en démarrer une nouvelle quand vous voulez !",
        "en": "It looks like you've stepped away — I'll close our session for now. Feel free to start a new one anytime!",
        "es": "Parece que se ha ausentado — voy a cerrar nuestra sesión. ¡No dude en iniciar una nueva cuando quiera!",
        "de": "Es sieht so aus, als wären Sie kurz weg — ich schließe unsere Sitzung jetzt. Starten Sie gerne jederzeit eine neue!",
        "ar": "يبدو أنك ابتعدت قليلاً — سأغلق جلستنا الآن. لا تتردد في بدء جلسة جديدة في أي وقت!",
        "ru": "Похоже, вы отошли — я закрою нашу сессию. Не стесняйтесь начать новую в любое время!",
    },
    "perfume_name_ack_instruction": {
        "fr": 'Dites UNE SEULE phrase courte et enthousiaste accueillant le nom de parfum "{name}" que l\'utilisateur vient de taper, puis dites que vous créez ses formules maintenant.',
        "en": 'Say ONE short enthusiastic sentence acknowledging the perfume name "{name}" the user just typed, then say you\'re creating their formulas now.',
        "es": 'Diga UNA sola frase corta y entusiasta reconociendo el nombre de perfume "{name}" que el usuario acaba de escribir, luego diga que está creando sus fórmulas ahora.',
        "de": 'Sage EINEN kurzen, begeisterten Satz, der den gerade eingegebenen Parfumnamen "{name}" aufgreift, und sage dann, dass du jetzt die Formeln erstellst.',
        "ar": 'قل جملة واحدة قصيرة وحماسية تتفاعل مع اسم العطر "{name}" الذي كتبه المستخدم للتو، ثم قل إنك تنشئ تركيباته الآن.',
        "ru": 'Скажи ОДНО короткое восторженное предложение, отмечая имя парфюма "{name}", которое пользователь только что напечатал, затем скажи, что ты сейчас создаёшь его формулы.',
    },
    "resume_instruction": {
        "fr": "L'utilisateur vient de cliquer sur le bouton pour reprendre. Ne vous présentez pas à nouveau. Dites simplement 'Je vous écoute, quelle est votre question ?' Soyez bref(ve) et naturel(le).",
        "en": "The user just clicked the button to resume. Do NOT re-introduce yourself. Simply say 'I'm all ears, what's your question?' Be brief and natural.",
        "es": "El usuario acaba de pulsar el botón para reanudar. No vuelva a presentarse. Simplemente diga 'Le escucho, ¿cuál es su pregunta?' Sea breve y natural.",
        "de": "Der Nutzer hat gerade den Button zum Fortsetzen geklickt. Stelle dich NICHT erneut vor. Sage einfach 'Ich höre zu, was ist Ihre Frage?' Sei kurz und natürlich.",
        "ar": "ضغط المستخدم للتو على الزر للمتابعة. لا تقدم نفسك مجددًا. قل فقط 'أنا أستمع، ما هو سؤالك؟' كن موجزًا وطبيعيًا.",
        "ru": "Пользователь только что нажал кнопку, чтобы продолжить. НЕ представляйся заново. Просто скажи 'Я слушаю, какой у вас вопрос?' Будь кратким и естественным.",
    },
    "continue_naturally": {
        "fr": "Continuez naturellement.",
        "en": "Continue naturally.",
        "es": "Continúe con naturalidad.",
        "de": "Fahre natürlich fort.",
        "ar": "تابع بشكل طبيعي.",
        "ru": "Продолжай естественно.",
    },
}


def t(key: str, lang: SupportedLanguage, **kwargs) -> str:
    text = TRANSLATIONS[key].get(lang, TRANSLATIONS[key]["fr"])
    return text.format(**kwargs) if kwargs else text


def err(detail: str, lang: SupportedLanguage) -> str:
    return f"{t('error', lang)}: {detail}"
