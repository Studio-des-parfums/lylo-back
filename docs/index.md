# Lylo Backend

Documentation technique du backend de l'expérience de création de parfum personnalisée pour **Le Studio des Parfums**.

---

## Qu'est-ce que Lylo ?

Lylo est un agent vocal IA qui guide l'utilisateur à travers un questionnaire olfactif pour générer deux formules de parfum personnalisées. L'utilisateur choisit ensuite une formule, peut la personnaliser, et la reçoit par email.

---

## 3 services qui tournent ensemble

| Service | Technologie | Rôle |
|---|---|---|
| **Backend API** | FastAPI + Python | Gère les sessions, les réponses, la génération de formules |
| **Agent vocal** | LiveKit Agents + OpenAI | Conduit la conversation et le questionnaire en voix |
| **Redis** | Redis 7 | Stocke l'état des sessions (TTL 1h) |

---

## Flux utilisateur en bref

```
Frontend → POST /session/start
              ↓
         Backend crée la session Redis + token LiveKit
              ↓
         Agent vocal rejoint la room LiveKit
              ↓
         Agent collecte le profil (prénom, genre, âge, allergies)
              ↓
         Agent pose 12 questions olfactives
              ↓
         POST /session/{id}/generate-formulas  →  2 formules générées
              ↓
         Utilisateur choisit + personnalise
              ↓
         Email envoyé automatiquement
```

---

## Par où commencer ?

- Nouveau sur le projet → [Installation](getting-started/installation.md)
- Comprendre l'architecture → [Vue d'ensemble](architecture/overview.md)
- Consulter les endpoints → [API Reference](api/sessions.md)
- Comprendre la génération de formules → [Logique métier](business/formula-generation.md)
