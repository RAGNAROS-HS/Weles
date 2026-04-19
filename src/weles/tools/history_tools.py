from typing import Any

from weles.agent.dispatch import ToolResult
from weles.db.history_repo import add_to_history as _add_to_history
from weles.db.history_repo import snooze_check_in as _snooze_check_in
from weles.db.history_repo import snooze_follow_up as _snooze_follow_up
from weles.db.settings_repo import get_setting

ADD_TO_HISTORY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_name": {
            "type": "string",
            "maxLength": 200,
            "description": "Name of the item (e.g. 'Red Wing 875', 'creatine monohydrate').",
        },
        "category": {
            "type": "string",
            "maxLength": 200,
            "description": "Item category (e.g. footwear, supplement, exercise).",
        },
        "domain": {
            "type": "string",
            "enum": ["shopping", "diet", "fitness", "lifestyle"],
            "description": "Domain this item belongs to.",
        },
        "status": {
            "type": "string",
            "enum": ["recommended", "bought", "tried", "rated", "skipped"],
            "description": "Item status.",
        },
        "rating": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "Optional rating 1–5.",
        },
        "notes": {
            "type": "string",
            "maxLength": 1000,
            "description": "Optional notes about the item.",
        },
    },
    "required": ["item_name", "category", "domain", "status"],
}


def add_to_history_handler(tool_input: dict[str, Any]) -> ToolResult:
    item = _add_to_history(
        item_name=tool_input["item_name"],
        category=tool_input["category"],
        domain=tool_input["domain"],
        status=tool_input["status"],
        rating=tool_input.get("rating"),
        notes=tool_input.get("notes"),
    )
    return ToolResult(summary=f"Saved {item['item_name']} to history.", data=item)


SNOOZE_FOLLOW_UP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_id": {
            "type": "string",
            "description": "ID of the history item to snooze (from the follow-up prompt context).",
        },
    },
    "required": ["item_id"],
}


def snooze_follow_up_handler(tool_input: dict[str, Any]) -> ToolResult:
    """Defer the follow-up for a recommended item by the configured cadence interval."""
    cadence = get_setting("follow_up_cadence") or "off"
    cadence_days = 7 if cadence == "weekly" else 30  # monthly fallback
    item_id = tool_input["item_id"]
    updated = _snooze_follow_up(item_id, cadence_days)
    if updated:
        return ToolResult(
            summary=f"Follow-up snoozed for {cadence_days} days.",
            data={"item_id": item_id, "snoozed_days": cadence_days},
        )
    return ToolResult(
        summary="Follow-up item not found.",
        data={"item_id": item_id},
    )


SNOOZE_CHECK_IN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_id": {
            "type": "string",
            "description": "ID of the history item to snooze (from the check-in prompt context).",
        },
    },
    "required": ["item_id"],
}


def snooze_check_in_handler(tool_input: dict[str, Any]) -> ToolResult:
    """Defer the check-in for a bought/tried item by 30 days ('Remind me later')."""
    item_id = tool_input["item_id"]
    updated = _snooze_check_in(item_id, days=30)
    if updated:
        return ToolResult(
            summary="Check-in snoozed for 30 days.",
            data={"item_id": item_id, "snoozed_days": 30},
        )
    return ToolResult(
        summary="Check-in item not found.",
        data={"item_id": item_id},
    )
