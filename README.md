# Lylo Backend

Backend de l'application Lilo pour Le Studio des Parfums — une experience de creation de parfum personnalisee guidee par un agent vocal IA.

## Architecture

Le projet est compose de 2 services :

- **Backend API** (FastAPI) — Gere les sessions, le profil utilisateur, les reponses au questionnaire et la generation de formules de parfum.
- **Agent vocal** (LiveKit Agents) — Se connecte a une room LiveKit et guide l'utilisateur par la voix a travers un questionnaire olfactif. Utilise Deepgram (STT), OpenAI (LLM) et Cartesia (TTS).

## Flux general

1. Le frontend demarre une session via l'API (`POST /api/session/start`)
2. Le backend cree la session avec les questions et retourne un token LiveKit
3. L'agent vocal rejoint la room LiveKit et commence la conversation
4. L'agent collecte le profil utilisateur (prenom, genre, age, allergies) puis pose les questions du questionnaire
5. Les reponses sont sauvegardees dans le stockage de session du backend via l'API
6. Une fois le questionnaire termine, l'agent declenche la generation de 2 formules de parfum personnalisees
7. Les formules sont envoyees au frontend via le Data Channel LiveKit

## Pre-requis

- Python 3.13+
- Un fichier `.env` a la racine du projet avec les cles API necessaires (LiveKit, Deepgram, Cartesia, OpenAI)

## Lancer le projet en local (developpement)

2 terminaux sont necessaires :

**Terminal 1** — Lancer le serveur API :

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

**Terminal 2** — Lancer l'agent vocal :

```bash
python3 agent.py dev
```

Le backend API tourne sur `http://localhost:8000`. Le flag `--reload` permet le rechargement automatique quand tu modifies le code.

## Build et deploiement (mise en ligne)

### Avec Docker Compose

Docker Compose permet de lancer les services d'un coup (API + Agent) :

```bash
# Build et lancement
docker compose up -d --build
```

Le flag `-d` lance les conteneurs en arriere-plan, et `--build` force la reconstruction des images.

Pour arreter les services :

```bash
docker compose down
```

### Build de l'image Docker seule

```bash
docker build -t lilo-backend .
```

### Lancer un service individuellement

```bash
# Seulement le backend API
docker run -p 8000:8000 --env-file .env lilo-backend

# Seulement l'agent vocal
docker run --env-file .env lilo-backend python agent.py start
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `LIVEKIT_URL` | URL du serveur LiveKit |
| `LIVEKIT_API_KEY` | Cle API LiveKit |
| `LIVEKIT_API_SECRET` | Secret API LiveKit |
| `DEEPGRAM_API_KEY` | Cle API Deepgram (STT) |
| `CARTESIA_API_KEY` | Cle API Cartesia (TTS) |
| `OPENAI_API_KEY` | Cle API OpenAI (LLM) |
| `VOICE_FR_FEMALE` | ID voix Cartesia FR feminine |
| `VOICE_FR_MALE` | ID voix Cartesia FR masculine |
| `VOICE_EN_FEMALE` | ID voix Cartesia EN feminine |
| `VOICE_EN_MALE` | ID voix Cartesia EN masculine |
| `BACKEND_URL` | URL du backend API (defaut: `http://localhost:8000`) |

---

## Tests Automatisés d’API avec Bruno (`/bruno`)

Une suite complète de 24 requêtes et 56 assertions automatisées couvre l'intégralité des routes de l'API.

Organisation des dossiers :
- `01-Consultation/` (14 requêtes) : **Lecture seule** (GET ping, speedtest, langues, catalogue questions/groupes/ingrédients, formules, sessions, branding, équipes, participants, imprimantes, clients). Garanti 0 écriture en base, 100 % sécurisé pour tester la **Production** ou le Local.
- `02-Creations-Modifications/` (10 requêtes) : **Cycles CRUD et mutations** (POST, PATCH, DELETE pour clients, membres d'équipe, participants).
- `03-Tous-Les-Tests/` (24 requêtes) : **Suite complète** regroupant l'ensemble des modules (Consultation + CRUD).

> ⚠️ **IMPORTANT — Nettoyage de la base de données :**
> Lorsque vous exécutez le dossier **`02-Creations-Modifications`** ou **`03-Tous-Les-Tests`**, des enregistrements de test temporaires peuvent être créés en base (`*Bruno*`).
> **Il faut impérativement exécuter le script de nettoyage après chaque exécution du dossier 02 ou 03 :**
> ```bash
> python scripts/cleanup_test_data.py
> ```

### Commandes d'exécution rapide (CLI)

1. **Tester la Production en toute sécurité (0 écriture) :**
```bash
cd bruno
bru run 01-Consultation -r --env prod
```

2. **Tester le Local en consultation seule :**
```bash
cd bruno
bru run 01-Consultation -r --env local
```

3. **Exécuter la suite complète en Local :**
```bash
cd bruno
bru run 03-Tous-Les-Tests -r --env local
# Toujours nettoyer la base après :
python ../scripts/cleanup_test_data.py
```

4. **Exécuter uniquement les mutations CRUD en Local :**
```bash
cd bruno
bru run 02-Creations-Modifications -r --env local
# Toujours nettoyer la base après :
python ../scripts/cleanup_test_data.py
```

