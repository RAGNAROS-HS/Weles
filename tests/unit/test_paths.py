import sys
from pathlib import Path

import pytest

from weles.utils.paths import resource_path


def test_resource_path_normal() -> None:
    path = resource_path("config/subreddits.toml")
    assert isinstance(path, Path)
    assert path.exists(), f"Expected {path} to exist"


def test_resource_path_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_meipass = "/tmp/fake_meipass"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", fake_meipass, raising=False)

    path = resource_path("config/subreddits.toml")
    assert path == Path(fake_meipass) / "config/subreddits.toml"
