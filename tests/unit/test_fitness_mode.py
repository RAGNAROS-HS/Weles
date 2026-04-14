"""Unit tests for Fitness mode: program filtering and injury_history system prompt injection."""

from weles.agent.prompts import build_system_prompt
from weles.profile.models import UserProfile
from weles.research.programs import filter_programs


def test_filter_programs_beginner_strength_barbell() -> None:
    """filter_programs('beginner', 'strength', 'barbell') returns GZCLP and Starting Strength."""
    results = filter_programs(level="beginner", goal="strength", equipment="barbell")
    names = [p["name"] for p in results]
    assert "GZCLP" in names
    assert "Starting Strength" in names


def test_filter_programs_excludes_non_matching() -> None:
    """filter_programs('beginner','strength','barbell') excludes intermediate/non-barbell."""
    results = filter_programs(level="beginner", goal="strength", equipment="barbell")
    names = [p["name"] for p in results]
    assert "5/3/1" not in names  # intermediate
    assert "C25K" not in names  # wrong goal and equipment


def test_fitness_system_prompt_includes_injury_history() -> None:
    """When injury_history is set, the fitness system prompt flags conflicting movements."""
    profile = UserProfile(injury_history="lower back herniation")
    blocks = build_system_prompt("fitness", profile, [])

    block_texts = " ".join(b["text"] for b in blocks)
    assert "lower back herniation" in block_texts
    assert "conflict" in block_texts


def test_fitness_system_prompt_no_injury_flag_when_unset() -> None:
    """When injury_history is not set, no injury flag is injected."""
    blocks = build_system_prompt("fitness", UserProfile(), [])

    block_texts = " ".join(b["text"] for b in blocks)
    assert "conflict with:" not in block_texts
