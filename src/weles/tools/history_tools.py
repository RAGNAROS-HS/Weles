from typing import Any

from weles.agent.dispatch import ToolResult
from weles.db.history_repo import add_to_history as _add_to_history

ADD_TO_HISTORY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "item_name": {
            "type": "string",
            "description": "Name of the item (e.g. 'Red Wing 875', 'creatine monohydrate').",
        },
        "category": {
            "type": "string",
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
