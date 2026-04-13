import tomllib
from typing import Any

from weles.utils.paths import resource_path

_subreddits: dict[str, Any] = {}


def _load() -> dict[str, Any]:
    global _subreddits
    if not _subreddits:
        path = resource_path("config/subreddits.toml")
        with open(path, "rb") as f:
            _subreddits = tomllib.load(f)
    return _subreddits


def get_subreddits(mode: str, subcategory: str | None) -> list[str]:
    """Return subreddits for the given mode and optional subcategory.

    Falls back to {mode}.general if subcategory not found.
    Falls back to ["BuyItForLife"] if mode not found entirely.
    """
    data = _load()
    mode_data = data.get(mode)
    if mode_data is None:
        return ["BuyItForLife"]

    if subcategory is not None:
        entry = mode_data.get(subcategory)
        if entry is not None:
            return list(entry["subreddits"])

    general = mode_data.get("general")
    if general is not None:
        return list(general["subreddits"])

    return ["BuyItForLife"]
