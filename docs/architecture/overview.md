# Vue d'ensemble

## Structure du projet

```
lylo-back/
├── main.py                        # Point d'entrée FastAPI (3 lignes)
├── agent.py                       # Agent vocal LiveKit (~830 lignes)
├── requirements.txt
├── docker-compose.yml
│
└── app/
    ├── config.py                  # Chargement des variables d'environnement
    ├── core/
    │   └── app_factory.py         # Setup FastAPI (CORS, routers, static files)
    ├── models/
    │   └── schemas.py             # Modèles Pydantic (requêtes/réponses)
    ├── routers/
    │   ├── sessions.py            # 15 endpoints sessions & formules
    │   └── mail.py                # 4 endpoints email/PDF
    ├── services/
    │   ├── session_service.py     # Création et récupération de session
    │   ├── formula_service.py     # Génération de formules (~750 lignes)
    │   ├── redis_service.py       # Persistance des sessions Redis
    │   ├── mail_service.py        # Génération HTML/PDF et envoi email
    │   └── livekit_service.py     # Tokens et rooms LiveKit
    └── data/
        ├── questions.py           # 12 questions bilingues (FR/EN)
        ├── choice_profile_mapping.py   # Choix → profils olfactifs
        ├── note_scoring_mapping.json   # Réponses → scores des notes
        └── profile_trait_mapping.json  # Descriptions des profils
```

## Responsabilités par fichier clé

| Fichier | Lignes | Rôle |
|---|---|---|
| `agent.py` | ~830 | Toute la logique de l'agent vocal : conversation, outils LLM, gestion d'état |
| `app/services/formula_service.py` | ~750 | Pipeline complet de génération de formules |
| `app/services/redis_service.py` | ~205 | CRUD des sessions dans Redis |
| `app/routers/sessions.py` | ~177 | Définition des endpoints API sessions |
| `app/data/questions.py` | ~177 | Données du questionnaire (12 questions, 2 langues) |

## Technologies utilisées

```
FastAPI          → API REST
LiveKit Agents   → Infrastructure de l'agent vocal
OpenAI GPT-4     → LLM pour la conversation
Deepgram         → Speech-to-Text
Cartesia         → Text-to-Speech
Bey              → Avatar vidéo
Redis            → Stockage des sessions
WeasyPrint       → Génération PDF
```
