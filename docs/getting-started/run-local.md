# Lancer en local

2 terminaux sont nécessaires pour faire tourner l'ensemble du projet.

## Terminal 1 — Backend API

```bash
uvicorn main:app --reload
```

Le serveur démarre sur `http://localhost:8000`.
Le flag `--reload` recharge automatiquement le code à chaque modification.

## Terminal 2 — Agent vocal

```bash
python3 agent.py dev
```

Le flag `dev` lance l'agent en mode développement avec des logs détaillés.

---

## Vérifier que tout tourne

- **API** : [http://localhost:8000/docs](http://localhost:8000/docs) — Swagger UI auto-généré par FastAPI
- **Redoc** : [http://localhost:8000/redoc](http://localhost:8000/redoc) — Documentation alternative

---

!!! tip "Astuce"
    FastAPI génère automatiquement une documentation Swagger interactive sur `/docs`. C'est utile pour tester les endpoints sans outil externe.
