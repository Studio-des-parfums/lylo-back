"""Construction du prompt système de l'agent : personnalité + mission de la phase courante.

Les textes vivent par étape du parcours :
  safety.py                    profil + questions de sécurité (toutes marques)
  questionnaire.py             questionnaire, générique selon le format (préférences / traits)
  result_formula.py            résultat « formule » (Lylo, Help)
  result_catalog.py            résultat « catalogue » (Ester)
  standby.py                   veille
Chaque marque (app/agent/brands/) assemble ces briques et surcharge ce qui diffère.
"""
