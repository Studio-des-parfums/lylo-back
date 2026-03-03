# Système de scoring

**Fichier :** `app/data/note_scoring_mapping.json`

## Principe

Chaque choix du questionnaire est mappé à des scores de notes de parfum. Quand l'utilisateur répond, ses `top_2` ajoutent des points et ses `bottom_2` en retirent.

## Poids des réponses

| Position | Poids |
|---|---|
| `top_2` (favoris) | **+2.0** |
| `bottom_2` (moins aimés) | **-1.0** |

## Mapping dans le JSON

Pour chaque choix, le JSON définit :

```json
"Plage": {
  "notes": {
    "Sel marin": 2,
    "Algue": 2,
    "Cèdre": 1
  },
  "families": {
    "Marin": 1,
    "Frais": 1
  }
}
```

- **`notes`** : scores directs sur des notes précises
- **`families`** : scores appliqués à toutes les notes appartenant à cette famille (fallback)

## Calcul du score final d'une note

```
score(note) = Σ (note_score × poids_réponse) + Σ (family_score × poids_réponse)
```

Le scoring est indépendant pour chaque catégorie : **top notes**, **heart notes**, **base notes**.

## Exemple

L'utilisateur met "Plage" en `top_2` (poids = +2) et "Désert" en `bottom_2` (poids = -1) :

```
Sel marin += 2 × 2 = +4
Algue     += 2 × 2 = +4
Cèdre     += 1 × 2 = +2

# Si Désert mappe { "Sable chaud": 2, "Épicé": 1 } :
Sable chaud += 2 × (-1) = -2
# Toutes les notes de famille "Épicé" += 1 × (-1) = -1
```
