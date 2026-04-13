from weles.agent.dispatch import ToolRegistry
from weles.tools.web import SEARCH_WEB_SCHEMA, search_web_handler


def _make_registry(web_search_available: bool) -> ToolRegistry:
    registry = ToolRegistry(max_calls=6)
    if web_search_available:
        registry.register("search_web", search_web_handler, SEARCH_WEB_SCHEMA)
    return registry


def test_search_web_excluded_when_web_search_unavailable() -> None:
    registry = _make_registry(web_search_available=False)
    names = [schema["name"] for schema in registry.get_tool_schemas()]
    assert "search_web" not in names


def test_search_web_included_when_web_search_available() -> None:
    registry = _make_registry(web_search_available=True)
    names = [schema["name"] for schema in registry.get_tool_schemas()]
    assert "search_web" in names
