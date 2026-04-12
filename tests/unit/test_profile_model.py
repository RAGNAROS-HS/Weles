import pytest
from pydantic import ValidationError

from weles.profile.models import UserProfile, profile_is_empty


def test_profile_is_empty_returns_true_for_default() -> None:
    assert profile_is_empty(UserProfile()) is True


def test_profile_is_empty_returns_false_when_field_set() -> None:
    assert profile_is_empty(UserProfile(fitness_level="beginner")) is False


def test_invalid_build_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        UserProfile(build="invalid")
