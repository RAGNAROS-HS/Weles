"""Unit tests for Diet mode system prompt: dietary restrictions constraint injection."""

from weles.agent.prompts import build_system_prompt
from weles.profile.models import UserProfile


def test_diet_prompt_with_restrictions_contains_hard_constraint() -> None:
    """When dietary_restrictions is set, the system prompt includes the hard constraints block."""
    profile = UserProfile(dietary_restrictions="gluten")
    blocks = build_system_prompt("diet", profile, [])

    block_texts = " ".join(b["text"] for b in blocks)
    assert "gluten" in block_texts
    assert "Hard constraints" in block_texts


def test_diet_prompt_without_restrictions_has_no_constraint_block() -> None:
    """When dietary_restrictions is not set, no hard constraints block is injected."""
    blocks = build_system_prompt("diet", UserProfile(), [])

    block_texts = " ".join(b["text"] for b in blocks)
    assert "Hard constraints" not in block_texts
