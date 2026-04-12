import logging

from weles.profile.models import Preference, UserProfile, profile_is_empty

logger = logging.getLogger(__name__)

_BUDGET_LABELS = {
    "buy_once_buy_right": "Buy once, buy right.",
    "good_enough": "Good enough.",
    "context_dependent": "Context dependent.",
}

# Rough token estimate: 4 characters ≈ 1 token
_CHARS_PER_TOKEN = 4
_TOKEN_WARNING_THRESHOLD = 500


def build_profile_block(profile: UserProfile, preferences: list[Preference]) -> str | None:
    """Serialise profile + preferences into a compact system block.

    Returns None when profile is empty and preferences list is empty.
    """
    if profile_is_empty(profile) and not preferences:
        return None

    lines: list[str] = ["[User Profile]"]

    # Body
    body_parts: list[str] = []
    if profile.height_cm is not None:
        body_parts.append(f"{profile.height_cm:g}cm")
    if profile.weight_kg is not None:
        body_parts.append(f"{profile.weight_kg:g}kg")
    if profile.build is not None:
        body_parts.append(f"{profile.build} build")
    if profile.fitness_level is not None:
        body_parts.append(f"{profile.fitness_level} fitness")
    if profile.activity_level is not None:
        body_parts.append(f"{profile.activity_level} activity")
    if body_parts:
        lines.append(f"Body: {', '.join(body_parts)}")

    # Injury history
    if profile.injury_history:
        lines.append(f"Injuries: {profile.injury_history}")

    # Diet
    has_diet = any(
        v is not None
        for v in (
            profile.dietary_restrictions,
            profile.dietary_approach,
            profile.dietary_preferences,
        )
    )
    if has_diet:
        diet_parts: list[str] = []
        if profile.dietary_restrictions:
            diet_parts.append(f"Restrictions: {profile.dietary_restrictions}.")
        if profile.dietary_approach is not None:
            diet_parts.append(f"Approach: {profile.dietary_approach}.")
        if profile.dietary_preferences:
            diet_parts.append(f"Preferences: {profile.dietary_preferences}.")
        lines.append(f"Diet: {' '.join(diet_parts)}")

    # Style
    style_parts: list[str] = []
    if profile.aesthetic_style is not None:
        style_parts.append(f"{profile.aesthetic_style} aesthetic.")
    if profile.brand_rejections:
        style_parts.append(f"Rejects: {profile.brand_rejections}.")
    if style_parts:
        lines.append(f"Style: {' '.join(style_parts)}")

    # Location
    location_parts: list[str] = []
    if profile.country:
        location_parts.append(f"{profile.country}.")
    if profile.climate:
        location_parts.append(f"Climate: {profile.climate}.")
    if profile.living_situation is not None:
        location_parts.append(f"Living: {profile.living_situation}.")
    if location_parts:
        lines.append(f"Location: {' '.join(location_parts)}")

    # Budget
    if profile.budget_psychology is not None:
        label = _BUDGET_LABELS.get(str(profile.budget_psychology), str(profile.budget_psychology))
        lines.append(f"Budget: {label}")

    # Goals
    goal_parts: list[str] = []
    if profile.fitness_goal:
        goal_parts.append(profile.fitness_goal)
    if profile.dietary_goal:
        goal_parts.append(profile.dietary_goal)
    if profile.lifestyle_focus:
        goal_parts.append(profile.lifestyle_focus)
    if goal_parts:
        lines.append(f"Goals: {' '.join(goal_parts)}")

    # Learned preferences
    if preferences:
        lines.append("Learned preferences:")
        for pref in preferences:
            lines.append(f"- {pref.value}")

    block = "\n".join(lines)

    # Warn if token estimate exceeds threshold (never truncate)
    estimated_tokens = len(block) // _CHARS_PER_TOKEN
    if estimated_tokens > _TOKEN_WARNING_THRESHOLD:
        logger.warning(
            "Profile context block is ~%d tokens (threshold: %d)",
            estimated_tokens,
            _TOKEN_WARNING_THRESHOLD,
        )

    return block
