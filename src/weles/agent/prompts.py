from pathlib import Path
from typing import Any

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def build_system_prompt(mode: str, profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    system_text = (_PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    return [{"type": "text", "text": system_text}]
