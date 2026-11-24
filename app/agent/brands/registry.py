from app.agent.brands.base import BrandProfile
from app.agent.brands.ester import EsterProfile
from app.agent.brands.help import HelpProfile
from app.agent.brands.lylo import LyloProfile

_PROFILES: dict[str, BrandProfile] = {p.slug: p() for p in (LyloProfile, EsterProfile, HelpProfile)}


def get_brand_profile(slug: str | None) -> BrandProfile:
    """Profil de la marque ; une marque sans profil dédié (créée dans le dashboard) suit Lylo."""
    return _PROFILES.get(slug or "lylo", _PROFILES["lylo"])
