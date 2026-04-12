import pytest

from weles.tools.profile_tools import save_profile_field


def test_save_profile_field_calls_update_profile(mocker) -> None:  # type: ignore[no-untyped-def]
    mock_update = mocker.patch("weles.tools.profile_tools.update_profile")
    save_profile_field("fitness_level", "beginner")
    mock_update.assert_called_once_with({"fitness_level": "beginner"})


def test_save_profile_field_unknown_field_raises() -> None:
    with pytest.raises(ValueError, match="Unknown profile field"):
        save_profile_field("unknown_field", "x")
