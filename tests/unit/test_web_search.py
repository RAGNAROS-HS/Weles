import pytest
from pytest_httpx import HTTPXMock

import weles.tools.web as web_module
from weles.tools.web import search_web

_TAVILY_URL = "https://api.tavily.com/search"


def _tavily_response(*results: dict) -> dict:
    return {"results": list(results), "answer": None}


def _result(title: str = "Title", url: str = "https://example.com/page") -> dict:
    return {"title": title, "url": url, "content": "Some snippet"}


@pytest.fixture(autouse=True)
def reset_domain_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web_module, "_community_domains", None)
    monkeypatch.setattr(web_module, "_commercial_domains", None)


@pytest.mark.asyncio
async def test_successful_response_parsed_into_web_results(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_TAVILY_URL,
        method="POST",
        json=_tavily_response(
            _result("Post One", "https://reddit.com/r/gadgets/1"),
            _result("Post Two", "https://amazon.com/product/2"),
        ),
    )

    results = await search_web("best headphones")

    assert len(results) == 2
    assert {r["title"] for r in results} == {"Post One", "Post Two"}
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "snippet" in r
        assert "domain" in r
        assert "source_type" in r


@pytest.mark.asyncio
async def test_community_domain_gets_community_source_type(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(web_module, "_community_domains", {"reddit.com"})
    monkeypatch.setattr(web_module, "_commercial_domains", set())
    httpx_mock.add_response(
        url=_TAVILY_URL,
        method="POST",
        json=_tavily_response(_result("Thread", "https://reddit.com/r/gadgets/abc")),
    )

    results = await search_web("query")

    assert results[0]["source_type"] == "community"


@pytest.mark.asyncio
async def test_commercial_domain_gets_commercial_source_type(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(web_module, "_community_domains", set())
    monkeypatch.setattr(web_module, "_commercial_domains", {"amazon.com"})
    httpx_mock.add_response(
        url=_TAVILY_URL,
        method="POST",
        json=_tavily_response(_result("Product", "https://amazon.com/product/123")),
    )

    results = await search_web("query")

    assert results[0]["source_type"] == "commercial"


@pytest.mark.asyncio
async def test_unknown_domain_gets_unknown_source_type(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(web_module, "_community_domains", set())
    monkeypatch.setattr(web_module, "_commercial_domains", set())
    httpx_mock.add_response(
        url=_TAVILY_URL,
        method="POST",
        json=_tavily_response(_result("Page", "https://somesite.example/page")),
    )

    results = await search_web("query")

    assert results[0]["source_type"] == "unknown"


@pytest.mark.asyncio
async def test_community_results_sorted_before_commercial(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(web_module, "_community_domains", {"reddit.com"})
    monkeypatch.setattr(web_module, "_commercial_domains", {"amazon.com"})
    httpx_mock.add_response(
        url=_TAVILY_URL,
        method="POST",
        json=_tavily_response(
            _result("Commercial First", "https://amazon.com/product/1"),
            _result("Community Second", "https://reddit.com/r/gadgets/2"),
        ),
    )

    results = await search_web("query")

    assert results[0]["source_type"] == "community"
    assert results[1]["source_type"] == "commercial"


@pytest.mark.asyncio
async def test_tavily_500_raises_exception(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_TAVILY_URL,
        method="POST",
        status_code=500,
    )

    import httpx

    with pytest.raises(httpx.HTTPStatusError):
        await search_web("query")
