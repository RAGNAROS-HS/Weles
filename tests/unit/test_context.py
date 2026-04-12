from weles.agent.context import check_missing_fields
from weles.profile.models import UserProfile


def test_shopping_empty_profile_returns_all_fields() -> None:
    result = check_missing_fields("shopping", UserProfile())
    assert result == ["budget_psychology", "aesthetic_style", "country"]


def test_shopping_one_field_set_excludes_it() -> None:
    result = check_missing_fields("shopping", UserProfile(budget_psychology="good_enough"))
    assert result == ["aesthetic_style", "country"]


def test_general_always_returns_empty() -> None:
    result = check_missing_fields("general", UserProfile())
    assert result == []


def test_diet_one_field_set_returns_other() -> None:
    result = check_missing_fields("diet", UserProfile(dietary_restrictions="gluten"))
    assert result == ["dietary_approach"]
