from weles.profile.models import UserProfile

_FIELDS_BY_MODE: dict[str, list[str]] = {
    "shopping": ["budget_psychology", "aesthetic_style", "country"],
    "diet": ["dietary_restrictions", "dietary_approach"],
    "fitness": ["fitness_level", "injury_history"],
    "lifestyle": ["living_situation", "climate"],
    "general": [],
}


def check_missing_fields(mode: str, profile: UserProfile) -> list[str]:
    """Return profile fields relevant to *mode* that are currently null."""
    relevant = _FIELDS_BY_MODE.get(mode, [])
    return [f for f in relevant if getattr(profile, f) is None]
