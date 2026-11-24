"""Marques : la liste vit en base (table `brands`, gérée depuis le dashboard).

Le code ne connaît que la marque par défaut et les marques à comportement spécifique
(ex. 'ester' = recommandation catalogue). Toute autre marque suit le comportement Lylo.
"""
from typing import Annotated

from pydantic import StringConstraints

DEFAULT_BRAND = "lylo"

# Identifiant technique : minuscules, chiffres, tirets (sert dans les URLs / NEXT_PUBLIC_BRAND).
BrandSlug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,19}$")]
