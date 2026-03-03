# Déploiement avec Docker Compose

## Services

`docker-compose.yml` lance les 3 services en une seule commande :

| Service | Image | Port | Dépend de |
|---|---|---|---|
| `redis` | `redis:7-alpine` | 6379 | — |
| `backend` | Build local | 8000 | redis |
| `agent` | Build local | — | backend |

## Lancer en production

```bash
# Build + lancement en arrière-plan
docker compose up -d --build

# Vérifier que les services tournent
docker compose ps

# Voir les logs
docker compose logs -f

# Arrêter
docker compose down
```

## Variables d'environnement

Les services utilisent le fichier `.env` à la racine. En production, les URLs internes sont automatiquement configurées :

- L'agent utilise `BACKEND_URL=http://backend:8000`
- L'agent utilise `REDIS_URL=redis://redis:6379`

## Build de l'image seule

```bash
docker build -t lilo-backend .
```

## Lancer un service individuellement

```bash
# Backend API uniquement
docker run -p 8000:8000 --env-file .env lilo-backend

# Agent vocal uniquement
docker run --env-file .env lilo-backend python agent.py start
```

## Notes importantes

!!! warning "Fichier .env"
    Le fichier `.env` doit être présent à la racine avant de lancer Docker Compose. Il n'est jamais inclus dans l'image Docker.

!!! info "Redémarrage automatique"
    En production, ajouter `restart: unless-stopped` dans `docker-compose.yml` pour que les services redémarrent automatiquement après un crash ou un reboot serveur.
