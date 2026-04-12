from typing import Any

from weles.profile.models import UserProfile, profile_is_empty
from weles.utils.paths import resource_path

_VALID_MODES = {"general", "shopping", "diet", "fitness", "lifestyle"}


def _build_profile_block_stub(profile: UserProfile) -> str:
    """Stub until #8 implements profile context injection. Always returns ''."""
    return ""


def build_system_prompt(
    mode: str,
    profile: UserProfile | None = None,
    preferences: list[Any] | None = None,
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

    # Block 3: profile context — stub until #8; _build_profile_block returns ""
    # so the block is skipped until the real implementation lands
    if profile is not None and not profile_is_empty(profile):
        profile_text = _build_profile_block_stub(profile)
        if profile_text:
            blocks.append({"type": "text", "text": profile_text})

    return blocks
