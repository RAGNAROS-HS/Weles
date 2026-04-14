"""Unit tests for context window management: estimated_tokens, Session.get_messages_for_context,
compression candidate selection, and the 80% compression threshold."""

from weles.agent.compression import _compression_candidates, needs_compression
from weles.agent.session import CONTEXT_WINDOW, Session, estimated_tokens


def test_estimated_tokens_empty_list() -> None:
    """estimated_tokens([]) returns 0."""
    assert estimated_tokens([]) == 0


def test_get_messages_for_context_substitutes_compressed_content() -> None:
    """get_messages_for_context() returns compressed messages with their summary content
    and strips the internal is_compressed field."""
    session = Session()
    session.add_message("user", "original question", is_compressed=False)
    session.add_message("assistant", "[Compressed] short summary", is_compressed=True)

    ctx = session.get_messages_for_context()

    assert len(ctx) == 2
    assert ctx[0] == {"role": "user", "content": "original question"}
    assert ctx[1] == {"role": "assistant", "content": "[Compressed] short summary"}
    assert "is_compressed" not in ctx[0]
    assert "is_compressed" not in ctx[1]


def test_last_10_messages_never_in_compression_candidates() -> None:
    """The last 10 messages are never in the compression candidate set."""
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(20)
    ]
    candidates = _compression_candidates(messages)
    last_10 = messages[-10:]
    for candidate in candidates:
        assert candidate not in last_10


def test_compression_not_triggered_below_threshold() -> None:
    """Session at 79% of CONTEXT_WINDOW does not trigger compression."""
    target_tokens = int(0.79 * CONTEXT_WINDOW)
    # estimated_tokens = word_count * 1.3; so word_count = target / 1.3
    word_count = int(target_tokens / 1.3)
    messages = [{"role": "user", "content": " ".join(["x"] * word_count)}]
    assert not needs_compression(messages)


def test_compression_triggered_above_threshold() -> None:
    """Session at 81% of CONTEXT_WINDOW triggers compression."""
    target_tokens = int(0.81 * CONTEXT_WINDOW)
    word_count = int(target_tokens / 1.3) + 1
    messages = [{"role": "user", "content": " ".join(["x"] * word_count)}]
    assert needs_compression(messages)
