"""Instantané des prompts de l'agent — filet de sécurité pour les refactors.

Génère get_prompt() pour toutes les combinaisons (phase × langue × marque × mode × ...)
et compare au snapshot commité (tests/snapshots/prompts.json, une empreinte par combinaison).

    python scripts/prompt_snapshot.py            # vérifie (code retour 1 si différence)
    python scripts/prompt_snapshot.py --update   # régénère le snapshot (changement voulu)
    python scripts/prompt_snapshot.py --dump DIR # écrit chaque prompt en clair (pour diff)

À lancer dans le conteneur backend (dépendances livekit) :
    docker compose -f docker-compose.local.yml exec backend python scripts/prompt_snapshot.py
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
logging.disable(logging.CRITICAL)

import agent  # noqa: E402

SNAPSHOT = ROOT / "tests" / "snapshots" / "prompts.json"

LANGS = ["fr", "en", "es", "de", "ar", "ru"]
BRANDS = ["lylo", "ester"]
INPUT_MODES = ["voice", "click"]
MODES = ["guided", "discovery"]
GENDERS = ["féminin", "masculin"]
QUESTIONS = [
    {
        "id": 100 + i,
        "question": f"Question {i}",
        "choices": [{"label": f"Choix {i}{c}", "image": ""} for c in "ABCD"],
    }
    for i in range(3)
]
QUESTION_INDEXES = [0, 1, 2]


def _render(phase, lang, brand, input_mode, mode, gender, q_index) -> str:
    state = agent.SessionState(
        phase=phase,
        current_question_index=q_index,
        current_top_2=["Choix A", "Choix B"],
        current_bottom_2=["Choix C", "Choix D"],
        profile={"first_name": "Camille", "gender": gender, "age": "30"},
        perfume_name="Aurore",
        formula_type="frais",
        selected_formula_index=0,
    )
    config = {"brand": brand, "questions": QUESTIONS, "mode": mode, "language": lang}
    return agent.get_prompt(state, config, "Rose", lang, input_mode)


def generate() -> dict[str, str]:
    prompts: dict[str, str] = {}
    for phase, lang, brand, input_mode, mode, gender, q_index in itertools.product(
        list(agent.AgentPhase), LANGS, BRANDS, INPUT_MODES, MODES, GENDERS, QUESTION_INDEXES
    ):
        key = f"{phase.name}|{lang}|{brand}|{input_mode}|{mode}|{gender}|q{q_index}"
        prompts[key] = _render(phase, lang, brand, input_mode, mode, gender, q_index)
    return prompts


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--dump", type=Path)
    args = parser.parse_args()

    prompts = generate()
    hashes = {key: digest(text) for key, text in prompts.items()}

    if args.dump:
        args.dump.mkdir(parents=True, exist_ok=True)
        for key, text in prompts.items():
            (args.dump / (key.replace("|", "__") + ".txt")).write_text(text, encoding="utf-8")
        print(f"{len(prompts)} prompts écrits dans {args.dump}")

    if args.update:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(hashes, indent=0, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Snapshot mis à jour : {len(hashes)} combinaisons, {len(set(hashes.values()))} prompts distincts")
        return 0

    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    changed = sorted(k for k in expected if hashes.get(k) != expected[k])
    added = sorted(set(hashes) - set(expected))
    if not changed and not added:
        print(f"OK — {len(hashes)} prompts identiques au snapshot")
        return 0
    print(f"DIFFÉRENCES — {len(changed)} modifiés/supprimés, {len(added)} nouveaux")
    for key in (changed + added)[:30]:
        print("  ", key)
    return 1


if __name__ == "__main__":
    sys.exit(main())
