# Redis & Sessions

## Structure des données

Chaque session est identifiée par un `session_id` (UUID). Les données sont réparties sur plusieurs clés Redis :

```
session:{session_id}:meta
session:{session_id}:profile
session:{session_id}:answers
session:{session_id}:generated_formulas
session:{session_id}:selected_formula
```

Toutes les clés ont un TTL de **1 heure**, remis à zéro à chaque écriture.

---

## Contenu de chaque clé

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

L'état courant de la session est calculé dynamiquement à partir des données Redis, via `GET /session/{id}/state`.

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
