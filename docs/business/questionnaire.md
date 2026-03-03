# Questionnaire olfactif

**Fichier :** `app/data/questions.py`

Le questionnaire est composé de **12 questions** disponibles en français et en anglais. Chaque question propose **6 choix illustrés**, et l'utilisateur doit désigner ses 2 préférés (`top_2`) et ses 2 moins aimés (`bottom_2`).

---

## Les 12 questions

| # | Thème | Choix proposés |
|---|---|---|
| 1 | **Destination** | Ville, Forêt, Campagne, Montagne, Désert, Plage |
| 2 | **Ville** | New York, Athènes, Delhi, Monsanto, Pékin, Tombouctou |
| 3 | **Restaurant** | Gastronomique, Salade, Couscous, Moléculaire, Steak House, Dessert |
| 4 | **Activité** | Sport, Rencontre, Promenade, Musée, Musique/Bar, Lecture |
| 5 | **Sport** | Endurance, Équipe, Précision, Aventure, Musculation, Agrément |
| 6 | **Musique** | Classique, Lyrique, Électronique, Jazz, World, Rock |
| 7 | **Matière** | Soie, Lin, Neige, Pierre, Bois, Ambre |
| 8 | **Plante** | Fleurs, Aromatique, Sauvage, Patchouli, Mousse, Foin |
| 9 | **Type de parfum** | Léger, Caractère, Vintage, Chaud, Frais, Moderne |
| 10 | **Matière première** | Musc, Ambre, Bois, Gourmand, Floral, Marin |
| 11 | **Couleur** | Marron, Vert, Rouge, Bleu, Jaune, Noir |
| 12 | **Type d'art** | Comprendre, Reconnaître, Imaginer, S'évader, S'interroger, S'émerveiller |

---

## Format d'une question

```python
{
  "id": 1,
  "text": {
    "fr": "Si tu devais choisir une destination...",
    "en": "If you had to choose a destination..."
  },
  "choices": {
    "fr": ["Ville", "Forêt", "Campagne", "Montagne", "Désert", "Plage"],
    "en": ["City", "Forest", "Countryside", "Mountain", "Desert", "Beach"]
  },
  "images": {
    "Ville": "/static/choices/1/ville.jpg",
    ...
  }
}
```

---

## Nombre de questions configurable

Le champ `question_count` dans `POST /session/start` permet de ne poser qu'un sous-ensemble des 12 questions (de 1 à 12). Les premières `question_count` questions de la liste sont utilisées.

---

## Comment les réponses influencent les formules

Voir → [Scoring](scoring.md)
