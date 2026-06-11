# Session Store & Sessions

## Structure des données

Chaque session est identifiée par un `session_id` (UUID). Les données sont réparties dans plusieurs structures en mémoire du process :

```
_meta[session_id]
_profiles[session_id]
_answers[session_id]
_generated_formulas[session_id]
_selected_formula[session_id]
```

Il n'y a pas de persistance externe ni de TTL. Les données sont perdues si le process redémarre.

---

## Contenu de chaque structure

### `:meta`
```json
{
  "language": "fr",
  "voice_gender": "female",
  "question_count": 12,
  "mode": "guided",
  "questions": [...],
  "room_name": "room_abc123",
  "agent_token": "..."
}
```

### `:profile`
```json
{
  "first_name": "Marie",
  "gender": "female",
  "age": "28",
  "has_allergies": "oui",
  "allergies": ["citral", "linalool"]
}
```

### `:answers`
```json
{
  "1": {
    "question_id": 1,
    "question_text": "...",
    "top_2": ["Plage", "Forêt"],
    "bottom_2": ["Désert", "Ville"]
  },
  "2": { ... }
}
```

### `:generated_formulas`
```json
[
  {
    "profile_name": "Visionary",
    "formula_type": "frais",
    "top_notes": [...],
    "heart_notes": [...],
    "base_notes": [...],
    "booster": {...},
    "quantities": { "10ml": {...}, "30ml": {...}, "50ml": {...} }
  },
  { ... }
]
```

### `:selected_formula`
La formule sélectionnée par l'utilisateur, enrichie des personnalisations (échanges de notes, changement de type).

---

## États de session

L'état courant de la session est calculé dynamiquement à partir des données du `session_store`, via `GET /session/{id}/state`.

| État | Condition |
|---|---|
| `collecting_profile` | Profil incomplet |
| `questionnaire` | Profil complet, réponses manquantes |
| `generating_formulas` | Toutes les réponses présentes, formules non générées |
| `completed` | Formules générées, aucune sélectionnée |
| `customization` | Formule sélectionnée |

!!! note "Profil complet"
    Les champs requis sont : `first_name`, `gender`, `age`, `has_allergies`.
    Si `has_allergies == "oui"` ou `"yes"`, le champ `allergies` est aussi requis.
