import json
from enum import StrEnum

from pydantic import BaseModel

_PROFILE_DATA_FIELDS = {
    "height_cm",
    "weight_kg",
    "build",
    "fitness_level",
    "injury_history",
    "dietary_restrictions",
    "dietary_preferences",
    "dietary_approach",
    "aesthetic_style",
    "brand_rejections",
    "climate",
    "activity_level",
    "living_situation",
    "country",
    "budget_psychology",
    "fitness_goal",
    "dietary_goal",
    "lifestyle_focus",
}


class Build(StrEnum):
    lean = "lean"
    athletic = "athletic"
    average = "average"
    heavy = "heavy"


class FitnessLevel(StrEnum):
    sedentary = "sedentary"
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class AestheticStyle(StrEnum):
    minimal = "minimal"
    technical = "technical"
    classic = "classic"
    mixed = "mixed"


class BudgetPsychology(StrEnum):
    buy_once_buy_right = "buy_once_buy_right"
    good_enough = "good_enough"
    context_dependent = "context_dependent"


class ActivityLevel(StrEnum):
    low = "low"
    moderate = "moderate"
    high = "high"


class LivingSituation(StrEnum):
    urban = "urban"
    suburban = "suburban"
    rural = "rural"


class DietaryApproach(StrEnum):
    keto = "keto"
    vegan = "vegan"
    omnivore = "omnivore"
    carnivore = "carnivore"
    flexible = "flexible"


class UserProfile(BaseModel):
    id: int | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    build: Build | None = None
    fitness_level: FitnessLevel | None = None
    injury_history: str | None = None
    dietary_restrictions: str | None = None
    dietary_preferences: str | None = None
    dietary_approach: DietaryApproach | None = None
    aesthetic_style: AestheticStyle | None = None
    brand_rejections: str | None = None
    climate: str | None = None
    activity_level: ActivityLevel | None = None
    living_situation: LivingSituation | None = None
    country: str | None = None
    budget_psychology: BudgetPsychology | None = None
    fitness_goal: str | None = None
    dietary_goal: str | None = None
    lifestyle_focus: str | None = None
    first_session_at: str | None = None
    field_timestamps: str | None = None


class Preference(BaseModel):
    id: str
    dimension: str
    value: str
    reason: str | None = None
    source: str
    created_at: str | None = None


def profile_is_empty(profile: UserProfile) -> bool:
    return all(getattr(profile, f) is None for f in _PROFILE_DATA_FIELDS)


def parse_field_timestamps(profile: UserProfile) -> dict[str, str]:
    result: dict[str, str] = json.loads(profile.field_timestamps or "{}")
    return result
