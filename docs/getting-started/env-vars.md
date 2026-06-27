# Variables d'environnement

Créer un fichier `.env` à la racine du projet. Ce fichier ne doit **jamais** être commité.

## Variables obligatoires

| Variable | Description |
|---|---|
| `LIVEKIT_URL` | URL du serveur LiveKit |
| `LIVEKIT_API_KEY` | Clé API LiveKit |
| `LIVEKIT_API_SECRET` | Secret API LiveKit |
| `DEEPGRAM_API_KEY` | Clé API Deepgram (STT) |
| `CARTESIA_API_KEY` | Clé API Cartesia (TTS) |
| `OPENAI_API_KEY` | Clé API OpenAI (LLM GPT-4) |
| `VOICE_FR_FEMALE` | ID de la voix Cartesia française féminine |
| `VOICE_FR_MALE` | ID de la voix Cartesia française masculine |
| `VOICE_EN_FEMALE` | ID de la voix Cartesia anglaise féminine |
| `VOICE_EN_MALE` | ID de la voix Cartesia anglaise masculine |

## Variables optionnelles

| Variable | Défaut | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | URL du backend API (utilisée par l'agent) |
| `RESEND_API_KEY` | — | Clé API Resend pour l'envoi d'emails |
| `RESEND_FROM` | — | Adresse expéditeur vérifiée sur un domaine validé dans Resend |
| `SMTP_HOST` | — | Hôte SMTP pour les emails |
| `SMTP_PORT` | — | Port SMTP |
| `SMTP_USER` | — | Utilisateur SMTP |
| `SMTP_PASSWORD` | — | Mot de passe SMTP |
| `SMTP_FROM` | — | Adresse expéditeur |
| `INTERNAL_EMAIL` | — | Email interne pour notif de sélection |

## Exemple de fichier `.env`

```env
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key
OPENAI_API_KEY=sk-...
VOICE_FR_FEMALE=voice_id_here
VOICE_FR_MALE=voice_id_here
VOICE_EN_FEMALE=voice_id_here
VOICE_EN_MALE=voice_id_here
BACKEND_URL=http://localhost:8000
RESEND_API_KEY=re_...
RESEND_FROM=no-reply@votredomaine.com
```
