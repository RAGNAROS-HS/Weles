from typing import Any

from weles.profile.context import build_profile_block
from weles.profile.models import Preference, UserProfile
from weles.utils.paths import resource_path

_VALID_MODES = {"general", "shopping", "diet", "fitness", "lifestyle"}


def build_system_prompt(
    mode: str,
    profile: UserProfile | None = None,
    preferences: list[Preference] | None = None,
) -> list[dict[str, Any]]:
    if mode not in _VALID_MODES:
        raise ValueError(f"Unknown mode: {mode!r}. Must be one of {sorted(_VALID_MODES)}")

    blocks: list[dict[str, Any]] = []

    # Block 1: base system prompt (always present)
    system_text = resource_path("src/weles/prompts/system.md").read_text(encoding="utf-8")
    blocks.append({"type": "text", "text": system_text})

    # Block 2: mode addendum (skipped for general)
    if mode != "general":
        mode_text = resource_path(f"src/weles/prompts/modes/{mode}.md").read_text(encoding="utf-8")
        blocks.append({"type": "text", "text": mode_text})

    # Block 3: profile context (omitted when profile is empty and no preferences)
    profile_text = build_profile_block(profile or UserProfile(), preferences or [])
    if profile_text:
        blocks.append({"type": "text", "text": profile_text})

    return blocks
