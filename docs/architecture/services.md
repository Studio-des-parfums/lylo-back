# Services

## session_service.py

Gère la création d'une nouvelle session et la récupération de ses données.

**Responsabilités :**
- Générer un `session_id` unique
- Créer la room LiveKit
- Générer le token LiveKit pour le frontend
- Stocker les métadonnées initiales dans le `session_store` (`language`, `voice_gender`, `mode`, `questions`)

---

## session_store.py

Couche de stockage en mémoire des sessions. Toutes les opérations de lecture/écriture des sessions passent par ici.

**Structures stockées par session :**

| Structure | Contenu |
|---|---|
| `_meta[session_id]` | Langue, voix, questions, room LiveKit |
| `_profiles[session_id]` | Prénom, genre, âge, allergies |
| `_answers[session_id]` | Réponses aux questions (par `question_id`) |
| `_generated_formulas[session_id]` | Les 2 formules générées |
| `_selected_formula[session_id]` | La formule choisie + personnalisations |

Les données sont conservées en mémoire du process et sont perdues si le service redémarre.

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
