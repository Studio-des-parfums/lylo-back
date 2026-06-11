# Installation

## Prérequis

- Python **3.13+**
- Un fichier `.env` à la racine (voir [Variables d'environnement](env-vars.md))

## Cloner le projet

```bash
git clone <repo-url>
cd lylo-back
```

## Installer les dépendances Python

```bash
pip install -r requirements.txt
```

## Dépendances principales

| Package | Rôle |
|---|---|
| `fastapi` / `uvicorn` | Serveur API |
| `livekit-agents` | Agent vocal |
| `livekit-plugins-openai` | LLM (GPT-4) |
| `livekit-plugins-deepgram` | Speech-to-Text |
| `livekit-plugins-cartesia` | Text-to-Speech |
| `livekit-plugins-bey` | Avatar vidéo |
| `openpyxl` | Lecture du coffret (XLSX) |
| `weasyprint` | Génération PDF |
