from unittest.mock import patch

import pytest

from weles.agent.prompts import build_system_prompt
from weles.profile.models import UserProfile


def test_general_mode_returns_one_block() -> None:
    blocks = build_system_prompt("general", None, [])
    assert len(blocks) == 1


def test_shopping_mode_returns_two_blocks() -> None:
    blocks = build_system_prompt("shopping", None, [])
    assert len(blocks) == 2
    assert "Shopping mode" in blocks[1]["text"]
    assert "subcategory" in blocks[1]["text"]


def test_unknown_mode_raises_value_error() -> None:
    with pytest.raises(ValueError):
        build_system_prompt("unknown_mode", None, [])


def test_non_empty_profile_adds_third_block() -> None:
    profile = UserProfile(fitness_level="beginner")
    blocks = build_system_prompt("shopping", profile, [])
    assert len(blocks) == 3


def test_empty_profile_does_not_add_third_block() -> None:
    blocks = build_system_prompt("shopping", UserProfile(), [])
    assert len(blocks) == 2


def test_build_system_prompt_does_not_read_files_on_repeated_calls() -> None:
    with patch("pathlib.Path.read_text") as mock_read:
        build_system_prompt("shopping", None, [])
        build_system_prompt("diet", None, [])
    mock_read.assert_not_called()
