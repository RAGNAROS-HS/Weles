import pytest

from weles.agent.dispatch import ToolRegistry
from weles.utils.errors import ToolNotFoundError


def test_register_and_dispatch_calls_handler():
    registry = ToolRegistry()
    registry.register("my_tool", lambda inp: "result", {"type": "object", "properties": {}})
    result = registry.dispatch("my_tool", {})
    assert result.summary == "result"
    assert result.data == "result"


def test_dispatch_unknown_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.dispatch("unknown", {})


def test_get_tool_schemas_returns_correct_keys():
    registry = ToolRegistry()
    registry.register("my_tool", lambda inp: inp, {"type": "object", "properties": {}})
    schemas = registry.get_tool_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "my_tool"
    assert "input_schema" in schemas[0]
