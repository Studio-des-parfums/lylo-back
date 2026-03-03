# Génération de formules

**Fichier :** `app/services/formula_service.py` (~750 lignes)

## Pipeline complet

```
Réponses du questionnaire
        ↓
   _score_notes()          — Score toutes les notes
        ↓
   _build_formula()        — Génère UNE formule
   ├─ _select_notes_by_score()    — Top N notes par catégorie
   ├─ _derive_profile_from_notes() — Profil olfactif
   ├─ _classify_formula_type()    — Type de formule
   ├─ _select_boosters()          — Sélection du booster
   └─ _compute_quantities()       — Calcul des ml
        ↓
[Répété 2 fois, les notes de la formule 1 sont exclues pour la formule 2]
```

---

## 1. Sélection des notes

Après le scoring, les notes sont classées par score décroissant. Le nombre de notes retenues dépend du type de formule :

| Type | Top notes | Heart notes | Base notes |
|---|---|---|---|
| `frais` | 3 | 3 | 2 |
| `mix` | 2 | 3 | 2 |
| `puissant` | 2 | 2 | 3 |

En cas d'égalité de score, la position dans le coffret (ordre alphabétique) sert de départage.

---

## 2. Dérivation du profil olfactif

10 profils possibles : `Strategist`, `Disruptor`, `Trailblazer`, `Visionary`, `Innovator`, `Creator`, `Influencer`, `Icon`, `Cosy`, ...

Chaque ingrédient dans le coffret a un `profile_1` (poids 2) et un `profile_2` (poids 1). Le profil de la formule est celui qui obtient le score cumulé le plus élevé parmi les notes sélectionnées.

---

## 3. Type de formule

Le type est déterminé par le profil olfactif selon une table de correspondance `profil → type` :

- Profils **masculins** → `puissant`
- Profils **féminins** → `frais`
- Profils **unisexes** → `mix`

Il peut être **forcé** via le paramètre `formula_type` dans la requête.

---

## 4. Sélection du booster

3 boosters fixes sont disponibles :

| Booster | Mots-clés associés |
|---|---|
| Floral | fleur, rose, jasmin, géranium, ... |
| Ambre doux | ambre, vanille, oriental, ... |
| Musc blanc sec | musc, propre, frais, coton, ... |

Le booster est choisi en fonction de ses correspondances avec les notes déjà sélectionnées.

---

## 5. Calcul des quantités

Pour chaque taille cible (10ml, 30ml, 50ml), les ml sont répartis entre les catégories selon le type de formule :

=== "Frais"
    | Catégorie | 10ml | 30ml | 50ml |
    |---|---|---|---|
    | Top notes | 1ml | 3ml | 5ml |
    | Heart notes | 1ml | 3ml | 5ml |
    | Base notes | 2ml | 6ml | 10ml |
    | Booster | 1ml | 3ml | 5ml |

=== "Mix"
    | Catégorie | 10ml | 30ml | 50ml |
    |---|---|---|---|
    | Top notes | 1ml | 3ml | 5ml |
    | Heart notes | 1ml | 3ml | 5ml |
    | Base notes | 2ml | 6ml | 10ml |
    | Booster | 1ml | 3ml | 5ml |

=== "Puissant"
    | Catégorie | 10ml | 30ml | 50ml |
    |---|---|---|---|
    | Top notes | 1ml | 3ml | 5ml |
    | Heart notes | 1ml | 3ml | 5ml |
    | Base notes | 2ml | 6ml | 10ml |
    | Booster | 1ml | 3ml | 5ml |

Les ml sont divisés équitablement entre les notes d'une même catégorie.

---

## 6. Gestion des allergies

Les ingrédients déclarés comme allergènes par l'utilisateur sont **exclus** de la sélection et des remplacements disponibles.

Le mapping allergènes est chargé depuis le fichier Excel du coffret (`Coffret-description.xlsx`).

---

## 7. Génération des 2 formules

1. Générer la formule **#1** (sans exclusions)
2. Exclure toutes les notes de la formule **#1**
3. Générer la formule **#2** avec les notes restantes

Les 2 formules sont ainsi garanties d'être différentes.
