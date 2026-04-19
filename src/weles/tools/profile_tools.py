from typing import Any

from weles.agent.dispatch import ToolResult
from weles.db.profile_repo import update_preference as _update_preference
from weles.db.profile_repo import update_profile

_VALID_FIELDS = {
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

SAVE_PROFILE_FIELD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "field": {
            "type": "string",
            "description": "Profile field name to update.",
        },
        "value": {
            "type": "string",
            "maxLength": 500,
            "description": "New value for the field.",
        },
    },
    "required": ["field", "value"],
}


def save_profile_field(field: str, value: str) -> str:
    """Save a single profile field. Raises ValueError for unknown fields."""
    if field not in _VALID_FIELDS:
        raise ValueError(f"Unknown profile field: {field!r}")
    update_profile({field: value})
    return f"Saved {field} = {value!r}"


def save_profile_field_handler(tool_input: dict[str, Any]) -> str:
    return save_profile_field(tool_input["field"], tool_input["value"])


UPDATE_PREFERENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "dimension": {
            "type": "string",
            "description": (
                "Preference dimension (e.g. 'shopping.footwear', 'diet.supplements'). "
                "Use 'domain.category' format."
            ),
        },
        "value": {
            "type": "string",
            "maxLength": 1000,
            "description": "Preference value (e.g. 'No minimalist styles', 'Avoids whey protein').",
        },
        "reason": {
            "type": "string",
            "maxLength": 1000,
            "description": "Optional: what the user said or did that prompted this preference.",
        },
    },
    "required": ["dimension", "value"],
}


def update_preference_handler(tool_input: dict[str, Any]) -> ToolResult:
    """Handle update_preference tool call; always writes with source='user_explicit'."""
    dimension = tool_input["dimension"]
    value = tool_input["value"]
    reason = tool_input.get("reason")
    _update_preference(dimension=dimension, value=value, reason=reason, source="user_explicit")
    return ToolResult(summary=f"Saved preference: {value}", data={"dimension": dimension})
