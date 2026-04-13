import os
from typing import Any, TypedDict
from urllib.parse import urlparse

import httpx

from weles.agent.dispatch import ToolResult
from weles.utils.paths import resource_path

_TAVILY_URL = "https://api.tavily.com/search"

_community_domains: set[str] | None = None
_commercial_domains: set[str] | None = None


def _load_domain_set(filename: str) -> set[str]:
    path = resource_path(f"blocklist/{filename}")
    domains: set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                domains.add(line.lower())
    except OSError:
        pass
    return domains


def _get_community_domains() -> set[str]:
    global _community_domains
    if _community_domains is None:
        _community_domains = _load_domain_set("community_domains.txt")
    return _community_domains


def _get_commercial_domains() -> set[str]:
    global _commercial_domains
    if _commercial_domains is None:
        _commercial_domains = _load_domain_set("commercial_domains.txt")
    return _commercial_domains


def preload_domain_sets() -> None:
    """Eagerly load domain sets at startup so missing files surface immediately."""
    _get_community_domains()
    _get_commercial_domains()


def _classify_domain(netloc: str) -> str:
    domain = netloc.lower().removeprefix("www.")
    if domain in _get_community_domains():
        return "community"
    if domain in _get_commercial_domains():
        return "commercial"
    return "unknown"


_SORT_ORDER = {"community": 0, "unknown": 1, "commercial": 2}


class WebResult(TypedDict):
    title: str
    url: str
    snippet: str
    domain: str
    source_type: str


async def search_web(query: str, limit: int = 8) -> list[WebResult]:
    api_key = os.getenv("TAVILY_API_KEY", "")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TAVILY_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": limit,
                "include_raw_content": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results: list[WebResult] = []
    for item in data.get("results", []):
        url = item.get("url", "")
        netloc = urlparse(url).netloc
        domain = netloc.lower().removeprefix("www.")
        source_type = _classify_domain(netloc)
        results.append(
            WebResult(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("content", ""),
                domain=domain,
                source_type=source_type,
            )
        )

    results.sort(key=lambda r: _SORT_ORDER.get(r["source_type"], 1))
    return results


SEARCH_WEB_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query."},
        "limit": {
            "type": "integer",
            "default": 8,
            "description": "Max results to return (default 8).",
        },
    },
    "required": ["query"],
}


async def search_web_handler(tool_input: dict[str, Any]) -> ToolResult:
    results = await search_web(
        query=tool_input["query"],
        limit=tool_input.get("limit", 8),
    )
    if not results:
        return ToolResult(summary="No results found.", data=[])
    return ToolResult(
        summary=f"Found {len(results)} results",
        data=results,
    )
