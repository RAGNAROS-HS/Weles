from weles.profile.context import build_profile_block
from weles.profile.models import Preference, UserProfile


def _pref(value: str) -> Preference:
    return Preference(id="p1", dimension="test", value=value, source="user_explicit")


def test_empty_profile_no_prefs_returns_none() -> None:
    assert build_profile_block(UserProfile(), []) is None


def test_non_empty_profile_returns_string_with_field() -> None:
    result = build_profile_block(UserProfile(fitness_level="beginner"), [])
    assert result is not None
    assert "beginner" in result


def test_null_field_not_in_output() -> None:
    result = build_profile_block(UserProfile(fitness_level="beginner"), [])
    assert result is not None
    assert "weight" not in result


def test_preferences_included_in_output() -> None:
    pref = _pref("No minimalist footwear")
    result = build_profile_block(UserProfile(fitness_level="beginner"), [pref])
    assert result is not None
    assert "No minimalist footwear" in result


def test_full_profile_token_estimate_under_500() -> None:
    profile = UserProfile(
        height_cm=178,
        weight_kg=80,
        build="athletic",
        fitness_level="intermediate",
        injury_history="bad knee",
        dietary_restrictions="lactose",
        dietary_preferences="high protein",
        dietary_approach="flexible",
        aesthetic_style="minimal",
        brand_rejections="fast fashion",
        climate="temperate",
        activity_level="high",
        living_situation="urban",
        country="PL",
        budget_psychology="buy_once_buy_right",
        fitness_goal="Build lean muscle",
        dietary_goal="Reduce processed food",
        lifestyle_focus="Sleep quality",
    )
    prefs = [_pref(f"Preference number {i}") for i in range(5)]
    result = build_profile_block(profile, prefs)
    assert result is not None
    estimated_tokens = len(result) // 4
    assert estimated_tokens < 500
