# API — Emails & PDF

---

## GET `/session/{session_id}/mail`

Retourne le HTML de la formule pour affichage dans le navigateur.

---

## GET `/session/{session_id}/mail/download`

Retourne la formule au format PDF téléchargeable (généré via `weasyprint`).

---

## POST `/session/{session_id}/mail/send`

Envoie la formule par email à l'adresse fournie.

**Body :**
```json
{
  "email": "client@example.com"
}
```

---

## POST `/mail/test`

Teste la connexion SMTP. Utile pour vérifier la configuration en production.

---

## Configuration SMTP

Le serveur utilise OVH MX Plan (`ssl0.ovh.net:587`). Les identifiants sont dans les [variables d'environnement](../getting-started/env-vars.md).
