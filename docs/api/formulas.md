# API — Formules

---

## POST `/session/{session_id}/generate-formulas`

Lance la génération des 2 formules de parfum personnalisées à partir des réponses du questionnaire.

**Body :**
```json
{
  "formula_type": null
}
```

`formula_type` peut être forcé à `"frais"`, `"mix"` ou `"puissant"`. Si `null`, le type est déterminé automatiquement par le scoring.

**Réponse :** Les 2 formules générées (voir structure ci-dessous).

---

## POST `/session/{session_id}/select-formula`

L'utilisateur sélectionne une des 2 formules proposées.

**Body :**
```json
{
  "formula_index": 0
}
```

`formula_index` : `0` ou `1`.

!!! note "Email automatique"
    Lors de la sélection, un email est envoyé automatiquement en tâche de fond à l'utilisateur et à l'adresse interne configurée.

---

## POST `/session/{session_id}/change-formula-type`

Modifie le type de la formule sélectionnée (recalcule les notes et quantités).

**Body :**
```json
{
  "formula_type": "puissant"
}
```

---

## GET `/session/{session_id}/available-ingredients/{note_type}`

Liste les ingrédients disponibles pour un type de note donné, filtrés par les allergies de l'utilisateur.

`note_type` : `"top"` | `"heart"` | `"base"`

---

## POST `/session/{session_id}/replace-note`

Remplace un ingrédient dans la formule sélectionnée et recalcule les quantités.

**Body :**
```json
{
  "note_type": "top",
  "old_note": "Bergamote",
  "new_note": "Citron"
}
```

---

## Structure d'une formule

```json
{
  "profile_name": "Visionary",
  "profile_description": "...",
  "formula_type": "frais",
  "top_notes": [
    { "name": "Bergamote", "family": "Agrumes", "quantities": { "10ml": 0.5, "30ml": 1.5, "50ml": 2.5 } }
  ],
  "heart_notes": [...],
  "base_notes": [...],
  "booster": {
    "name": "Musc blanc sec",
    "quantities": { "10ml": 1, "30ml": 3, "50ml": 5 }
  }
}
```
