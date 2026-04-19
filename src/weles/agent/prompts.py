import tomllib
from typing import Any

from weles.profile.context import build_profile_block
from weles.profile.models import Preference, UserProfile
from weles.utils.paths import resource_path

_SYSTEM_TEXT: str = resource_path("src/weles/prompts/system.md").read_text(encoding="utf-8")
_RESEARCH_TEXT: str = resource_path("src/weles/prompts/research.md").read_text(encoding="utf-8")
_MODE_TEXTS: dict[str, str] = {
    mode: resource_path(f"src/weles/prompts/modes/{mode}.md").read_text(encoding="utf-8")
    for mode in ("shopping", "diet", "fitness", "lifestyle")
}


def _load_programs_text() -> str:
    path = resource_path("config/programs.toml")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    programs = data.get("programs", [])
    lines = ["Community-vetted programs:"]
    for p in programs:
        line = (
            f"- {p['name']} | level: {p['level']} | goal: {p['goal']} | equipment: {p['equipment']}"
        )
        if p.get("source"):
            line += f" | source: {p['source']}"
        lines.append(line)
    return "\n".join(lines)


_PROGRAMS_TEXT: str = _load_programs_text()

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
    blocks.append({"type": "text", "text": _SYSTEM_TEXT})

    # Block 2: mode addendum + optional hard constraints + research guidelines (skipped for general)
    if mode != "general":
        combined = _MODE_TEXTS[mode]
        if mode == "diet" and profile and profile.dietary_restrictions:
            constraint = (
                f"Hard constraints: user cannot eat {profile.dietary_restrictions}. "
                "Never suggest items containing these. "
                "Discard research results that include them."
            )
            combined = combined + "\n\n" + constraint
        if mode == "fitness":
            combined = combined + "\n\n" + _PROGRAMS_TEXT
            if profile and profile.injury_history:
                combined = (
                    combined
                    + "\n\nFlag if any recommended program includes movements that may"
                    + f" conflict with: {profile.injury_history}."
                )
        blocks.append({"type": "text", "text": combined + "\n\n" + _RESEARCH_TEXT})

    # Block 3: profile context (omitted when profile is empty and no preferences)
    profile_text = build_profile_block(profile or UserProfile(), preferences or [])
    if profile_text:
        blocks.append({"type": "text", "text": profile_text})

    return blocks
