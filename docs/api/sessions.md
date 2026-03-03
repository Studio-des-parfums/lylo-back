# API — Sessions

Base URL : `/api`

---

## POST `/session/start`

Crée une nouvelle session et retourne un token LiveKit pour que le frontend rejoigne la room.

**Body :**
```json
{
  "language": "fr",
  "voice_gender": "female",
  "question_count": 12,
  "mode": "guided"
}
```

| Champ | Type | Valeurs |
|---|---|---|
| `language` | string | `"fr"` \| `"en"` |
| `voice_gender` | string | `"female"` \| `"male"` |
| `question_count` | int | 1–12 |
| `mode` | string | `"guided"` \| `"discovery"` |

**Réponse :**
```json
{
  "session_id": "uuid",
  "room_name": "room_abc",
  "token": "livekit_access_token",
  "livekit_url": "wss://...",
  "identity": "user_identity"
}
```

---

## GET `/session/{session_id}`

Retourne les métadonnées d'une session (langue, voix, questions, room).

---

## DELETE `/session/{session_id}`

Supprime la session Redis et la room LiveKit associée.

---

## GET `/session_list`

Liste tous les `session_id` actifs dans Redis.

---

## POST `/session/{session_id}/save-answer`

Enregistre la réponse à une question du questionnaire.

**Body :**
```json
{
  "question_id": 3,
  "question_text": "Quel type de restaurant préférez-vous ?",
  "top_2": ["Gastronomique", "Salade"],
  "bottom_2": ["Steak House", "Dessert"]
}
```

---

## GET `/session/{session_id}/answers`

Retourne toutes les réponses enregistrées pour la session.

---

## POST `/session/{session_id}/save-profile`

Enregistre un champ du profil utilisateur.

**Body :**
```json
{
  "field": "first_name",
  "value": "Marie"
}
```

| `field` | Description |
|---|---|
| `first_name` | Prénom |
| `gender` | `"male"` \| `"female"` \| `"non-binary"` |
| `age` | Âge (string) |
| `has_allergies` | `"oui"` / `"non"` / `"yes"` / `"no"` |
| `allergies` | Nom des allergènes (si `has_allergies == "oui"`) |

---

## GET `/session/{session_id}/profile`

Retourne le profil complet de l'utilisateur.

---

## GET `/session/{session_id}/state`

Retourne l'état courant de la session et indique si le profil est complet.

**Réponse :**
```json
{
  "state": "questionnaire",
  "profile_complete": true,
  "answers_count": 7
}
```

---

## GET `/sessions/all-answers`

Export de toutes les réponses de toutes les sessions actives (usage interne/analytics).
