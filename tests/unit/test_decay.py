"""Unit tests for profile field decay detection (issue #28)."""

import json
from datetime import datetime, timedelta

from weles.profile.decay import check_decay
from weles.profile.models import UserProfile

_THRESHOLDS = {
    "goals": 60,
    "fitness_level": 90,
    "dietary_approach": 90,
    "body_metrics": 180,
    "taste_lifestyle": 365,
}


def _make_profile(**field_ages: int) -> UserProfile:
    """Build a UserProfile with the given fields set to non-null values,
    with timestamps aged by the specified number of days.
    """
    now = datetime.utcnow()
    data: dict = {}
    timestamps: dict = {}
    defaults = {
        "fitness_goal": "build muscle",
        "dietary_goal": "lose weight",
        "lifestyle_focus": "minimalism",
        "fitness_level": "intermediate",
        "dietary_approach": "flexible",
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "build": "athletic",
        "aesthetic_style": "minimal",
        "activity_level": "moderate",
        "living_situation": "urban",
        "climate": "temperate",
        "budget_psychology": "good_enough",
    }
    for field, days_ago in field_ages.items():
        data[field] = defaults[field]
        timestamps[field] = (now - timedelta(days=days_ago)).isoformat()
    data["field_timestamps"] = json.dumps(timestamps)
    return UserProfile(**data)


def test_check_decay_all_fresh_returns_none() -> None:
    """check_decay returns None when all fields were updated recently."""
    profile = _make_profile(fitness_goal=10, fitness_level=30)
    result = check_decay(profile, _THRESHOLDS)
    assert result is None


def test_check_decay_stale_field_returns_prompt() -> None:
    """check_decay returns a decay prompt when fitness_goal is 61 days old (threshold: 60)."""
    profile = _make_profile(fitness_goal=61)
    result = check_decay(profile, _THRESHOLDS)
    assert result is not None
    assert result.type == "decay"
    assert "fitness goal" in result.message
    assert "61 days" in result.message
    assert "build muscle" in result.message


def test_check_decay_null_field_not_stale() -> None:
    """Null fields are never returned as stale (they have no timestamp)."""
    # Profile with no fields set → all None → no timestamps
    profile = UserProfile()
    result = check_decay(profile, _THRESHOLDS)
    assert result is None


def test_check_decay_most_overdue_field_selected() -> None:
    """When multiple fields are stale, the most overdue (largest overage) is returned."""
    # fitness_goal: 61 days old, threshold 60 → overage 1
    # fitness_level: 100 days old, threshold 90 → overage 10  ← most overdue
    profile = _make_profile(fitness_goal=61, fitness_level=100)
    result = check_decay(profile, _THRESHOLDS)
    assert result is not None
    assert "fitness level" in result.message


def test_check_decay_thresholds_configurable() -> None:
    """Thresholds are read from the passed dict; custom threshold respected."""
    profile = _make_profile(fitness_goal=30)
    # With a threshold of 20 days for "goals", 30 days is stale
    result = check_decay(profile, {"goals": 20})
    assert result is not None
    assert "fitness goal" in result.message

    # With threshold of 60 days, 30 days is fresh
    result_fresh = check_decay(profile, {"goals": 60})
    assert result_fresh is None
