# Agent vocal

## Stack technique

| Composant | Service |
|---|---|
| Infrastructure | LiveKit Agents |
| LLM | OpenAI GPT-4 |
| Speech-to-Text | Deepgram |
| Text-to-Speech | Cartesia |
| Avatar vidéo | Bey |

## Modes de fonctionnement

L'agent supporte deux modes, définis au démarrage de la session :

- **`guided`** — L'agent suit strictement le questionnaire, question par question.
- **`discovery`** — L'agent a une conversation plus libre et exploratoire sur les préférences olfactives.

## Outils LLM disponibles (function tools)

L'agent dispose de plusieurs outils qu'il peut appeler via le LLM :

| Outil | Description |
|---|---|
| `save_user_profile(field, value)` | Enregistre un champ du profil utilisateur |
| `notify_top_2(question_id, top_2)` | Notifie le frontend des 2 choix favoris (pour l'UI) |
| `save_answer(question_id, question_text, top_2, bottom_2)` | Enregistre une réponse complète |
| `generate_formulas(formula_type)` | Lance la génération des 2 formules |
| `select_formula(formula_index)` | Sélectionne la formule 0 ou 1 |
| `get_available_ingredients(note_type)` | Liste les ingrédients disponibles par type (filtrés par allergies) |
| `replace_note(note_type, old_note, new_note)` | Remplace un ingrédient dans la formule |
| `change_formula_type(formula_type)` | Change le type de la formule (frais/mix/puissant) |
| `enter_pause_mode()` | Met l'agent en veille après les au revoir |

## Communication avec le frontend

L'agent envoie des mises à jour d'état au frontend via le **LiveKit Data Channel** (topic : `"state"`).

Exemple de message envoyé :
```json
{
  "type": "state",
  "state": "questionnaire",
  "current_question": 3
}
```

## Avatars

| Genre | ID Bey |
|---|---|
| Féminin | `694c83e2-8895-4a98-bd16-56332ca3f449` |
| Masculin | `b63ba4e6-d346-45d0-ad28-5ddffaac0bd0_v2` |

## Lancer l'agent

```bash
# Développement (logs détaillés)
python3 agent.py dev

# Production
python3 agent.py start
```
