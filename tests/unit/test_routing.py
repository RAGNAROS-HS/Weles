from weles.research.routing import get_subreddits


def test_shopping_footwear():
    assert get_subreddits("shopping", "footwear") == [
        "goodyearwelt",
        "BuyItForLife",
        "malefashionadvice",
    ]


def test_shopping_nonexistent_subcategory_falls_back_to_general():
    result = get_subreddits("shopping", "nonexistent")
    assert result == ["BuyItForLife", "frugalmalefashion", "femalefashionadvice"]


def test_nonexistent_mode_returns_fallback():
    assert get_subreddits("nonexistent_mode", None) == ["BuyItForLife"]


def test_fitness_running():
    assert get_subreddits("fitness", "running") == ["running", "trailrunning", "BuyItForLife"]


def test_valid_mode_no_subcategory_returns_general():
    assert get_subreddits("diet", None) == ["nutrition", "EatCheapAndHealthy", "MealPrepSunday"]
