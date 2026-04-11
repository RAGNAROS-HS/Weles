import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Return absolute path to a resource, compatible with PyInstaller bundles."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / relative  # type: ignore[attr-defined]
    return Path(__file__).parent.parent.parent.parent / relative
