# Services

## session_service.py

Gère la création d'une nouvelle session et la récupération de ses données.

**Responsabilités :**
- Générer un `session_id` unique
- Créer la room LiveKit
- Générer le token LiveKit pour le frontend
- Stocker les métadonnées initiales dans Redis (`language`, `voice_gender`, `question_count`, `mode`, `questions`)

---

## redis_service.py

Couche d'accès à Redis. Toutes les opérations de lecture/écriture des sessions passent par ici.

**Clés Redis par session :**

| Clé | Contenu |
|---|---|
| `session:{id}:meta` | Langue, voix, questions, room LiveKit |
| `session:{id}:profile` | Prénom, genre, âge, allergies |
| `session:{id}:answers` | Réponses aux questions (par `question_id`) |
| `session:{id}:generated_formulas` | Les 2 formules générées |
| `session:{id}:selected_formula` | La formule choisie + personnalisations |

**TTL :** 1 heure (3600s) — toutes les clés sont remises à jour à chaque écriture.

---

## formula_service.py

Le cœur du projet. Voir la page dédiée → [Génération de formules](../business/formula-generation.md).

---

## livekit_service.py

Gère les interactions avec l'API LiveKit :
- Création de room
- Génération de tokens d'accès (pour le frontend et l'agent)
- Suppression de room

---

## mail_service.py

**Génération HTML :** Produit une page HTML avec le profil olfactif, la pyramide de notes, les ingrédients et les quantités par taille (10/30/50ml).

**Génération PDF :** Convertit le HTML via `weasyprint` avec les images en base64.

**Envoi email :** Via SMTP (OVH ssl0.ovh.net:587). Deux emails sont envoyés lors de la sélection d'une formule :
1. Un email à l'utilisateur avec sa formule
2. Une notification interne (`INTERNAL_EMAIL`)
