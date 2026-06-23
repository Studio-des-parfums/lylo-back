# API — Participants

Base URL : `/participants`

---

## POST `/`

Crée ou met à jour un participant à partir des informations saisies par le frontend, sans `session_id`.

**Body :**
```json
{
  "first_name": "Marie",
  "last_name": "Durand",
  "email": "marie@example.com",
  "phone": "0600000000"
}
```

**Réponse :**
```json
{
  "id": 12,
  "first_name": "Marie",
  "last_name": "Durand",
  "email": "marie@example.com",
  "phone": "0600000000",
  "created_at": "2026-06-23T12:00:00+00:00"
}
```

---

## GET `/`

Liste les participants.

---

## GET `/{participant_id}`

Retourne un participant par son identifiant.
