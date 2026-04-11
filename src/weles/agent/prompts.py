from typing import Any

from weles.utils.paths import resource_path


def build_system_prompt(mode: str, profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    system_text = resource_path("src/weles/prompts/system.md").read_text(encoding="utf-8")
    return [{"type": "text", "text": system_text}]
