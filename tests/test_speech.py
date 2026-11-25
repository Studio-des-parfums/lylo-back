from app.agent.speech import resolve_gender_forms


def test_feminine_forms():
    assert resolve_gender_forms("En calma, solo/a", True) == "En calma, sola"
    assert resolve_gender_forms("Rodeado/a de tus seres queridos", True) == "Rodeada de tus seres queridos"
    assert resolve_gender_forms("todos/as", True) == "todas"
    assert resolve_gender_forms("seul(e) au calme", True) == "seule au calme"


def test_masculine_or_unknown_forms():
    assert resolve_gender_forms("En calma, solo/a", False) == "En calma, solo"
    assert resolve_gender_forms("seul(e)", False) == "seul"


def test_non_gender_slashes_untouched():
    assert resolve_gender_forms("et/ou 50 km/h", True) == "et/ou 50 km/h"
