import pytest

from weles.agent.dispatch import ToolRegistry
from weles.utils.errors import MaxToolCallsError


def test_7th_dispatch_raises_max_tool_calls_error() -> None:
    registry = ToolRegistry(max_calls=6)
    registry.register("t", lambda _: "ok", {"type": "object", "properties": {}})

    for _ in range(6):
        registry.dispatch("t", {})

    with pytest.raises(MaxToolCallsError):
        registry.dispatch("t", {})
