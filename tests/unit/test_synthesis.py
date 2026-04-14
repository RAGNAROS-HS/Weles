from weles.agent.stream import _build_failure_message


def test_single_failed_tool_produces_failure_message():
    msg = _build_failure_message(["search_reddit"])
    assert msg is not None
    assert "search_reddit" in msg
    assert "Continue with available data" in msg
    assert "which sources were unavailable" in msg


def test_empty_failed_tools_produces_no_message():
    assert _build_failure_message([]) is None
