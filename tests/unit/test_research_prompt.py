"""Unit tests for research.md confidence calibration labels (issue #29)."""

from weles.utils.paths import resource_path


def _research_md() -> str:
    return resource_path("src/weles/prompts/research.md").read_text(encoding="utf-8")


def test_research_md_contains_strong_consensus() -> None:
    """research.md contains the [strong consensus] label."""
    assert "[strong consensus]" in _research_md()


def test_research_md_contains_divided_community() -> None:
    """research.md contains the [divided community] label."""
    assert "[divided community]" in _research_md()


def test_research_md_contains_thin_data() -> None:
    """research.md contains the [thin data] label."""
    assert "[thin data]" in _research_md()
