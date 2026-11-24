from app.agent.brands.lylo import LyloProfile
from app.agent.prompts import result_catalog


class EsterProfile(LyloProfile):
    """Recommande 2 parfums existants du catalogue au lieu de créer une formule."""

    slug = "ester"
    result_engine = "catalog"
    missions = {**LyloProfile.missions, **result_catalog.MISSIONS}
