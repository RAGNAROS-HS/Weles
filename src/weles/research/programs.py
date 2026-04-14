import tomllib
from typing import Any

from weles.utils.paths import resource_path

_programs: list[dict[str, Any]] | None = None


def _load() -> list[dict[str, Any]]:
    global _programs
    if _programs is None:
        path = resource_path("config/programs.toml")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        _programs = data.get("programs", [])
    return _programs


def filter_programs(
    level: str | None = None,
    goal: str | None = None,
    equipment: str | None = None,
) -> list[dict[str, Any]]:
    """Return programs matching all provided filters (None = no filter on that field)."""
    results = []
    for prog in _load():
        if level and prog.get("level") != level:
            continue
        if goal and prog.get("goal") != goal:
            continue
        if equipment and prog.get("equipment") != equipment:
            continue
        results.append(prog)
    return results
