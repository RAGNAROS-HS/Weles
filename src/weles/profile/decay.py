"""Profile field decay detection.

Returns a reconfirmation prompt for the most-overdue stale field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from weles.profile.models import UserProfile, parse_field_timestamps

# Maps profile field name → decay_thresholds settings key
FIELD_DECAY_CATEGORY: dict[str, str] = {
    "fitness_goal": "goals",
    "dietary_goal": "goals",
    "lifestyle_focus": "goals",
    "fitness_level": "fitness_level",
    "dietary_approach": "dietary_approach",
    "height_cm": "body_metrics",
    "weight_kg": "body_metrics",
    "build": "body_metrics",
    "aesthetic_style": "taste_lifestyle",
    "activity_level": "taste_lifestyle",
    "living_situation": "taste_lifestyle",
    "climate": "taste_lifestyle",
    "budget_psychology": "taste_lifestyle",
}


@dataclass
class DecayPrompt:
    """Prompt returned when a profile field has passed its decay threshold."""

    type: str  # always "decay"
    message: str


def check_decay(profile: UserProfile, thresholds: dict[str, int]) -> DecayPrompt | None:
    """Return a decay prompt for the most-overdue stale profile field.

    Only non-null fields with a recorded timestamp are evaluated.
    Returns None when no field has exceeded its threshold.
    """
    timestamps = parse_field_timestamps(profile)
    now = datetime.utcnow()

    best: tuple[int, str, int, str] | None = None  # (overage_days, field_name, age_days, value)

    for field_name, category in FIELD_DECAY_CATEGORY.items():
        ts_str = timestamps.get(field_name)
        if not ts_str:
            continue
        value = getattr(profile, field_name, None)
        if value is None:
            continue
        threshold_days = thresholds.get(category, 365)
        try:
            ts = datetime.fromisoformat(ts_str)
        except ValueError:
            continue
        age_days = (now - ts).days
        if age_days >= threshold_days:
            overage = age_days - threshold_days
            if best is None or overage > best[0]:
                best = (overage, field_name, age_days, str(value))

    if best is None:
        return None

    _, field_name, age_days, value_str = best
    label = field_name.replace("_", " ")
    return DecayPrompt(
        type="decay",
        message=f"Your {label} was last set {age_days} days ago as '{value_str}'. Still accurate?",
    )
