from app.agent.profile_validation import validate


def test_gender_binary_only():
    assert validate("gender", "C'est bien. Masculin.") == ("masculin", None)
    assert validate("gender", "Femenino") == ("féminin", None)
    assert validate("gender", "une femme") == ("féminin", None)
    for answer in ("ni masculin ni féminin", "je préfère ne pas dire", "non précisé", "masculin et féminin"):
        value, refusal = validate("gender", answer)
        assert value is None and refusal.startswith("[rejected]")


def test_age_required_and_bounded():
    assert validate("age", "26") == ("26", None)
    assert validate("age", "vingt-six")[0] is None  # le LLM doit passer le nombre
    assert validate("age", "150")[0] is None


def test_yes_no_required():
    assert validate("has_allergies", "Non.") == ("non", None)
    assert validate("pregnant", "sí") == ("oui", None)
    assert validate("has_disliked_notes", "je ne sais pas")[0] is None


def test_first_name():
    assert validate("first_name", "Patrice") == ("Patrice", None)
    assert validate("first_name", "Plus la merde à voir")[0] is None
