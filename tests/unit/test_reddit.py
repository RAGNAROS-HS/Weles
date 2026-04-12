import pytest
from pytest_httpx import HTTPXMock

from weles.tools.reddit import search_reddit
from weles.utils.errors import RedditUnavailableError

_BASE = "https://www.reddit.com"


def _post(title: str = "Test Post", score: int = 100, post_id: str = "abc1") -> dict:
    return {
        "kind": "t3",
        "data": {
            "title": title,
            "url": f"{_BASE}/r/BuyItForLife/comments/{post_id}/test/",
            "score": score,
            "created_utc": 1700000000.0,
            "subreddit": "BuyItForLife",
            "selftext": "Some body text here",
            "id": post_id,
            "permalink": f"/r/BuyItForLife/comments/{post_id}/test/",
        },
    }


def _listing(*posts: dict) -> dict:
    return {"kind": "Listing", "data": {"children": list(posts)}}


def _comments(*bodies: tuple[str, int]) -> list:
    children = [{"kind": "t1", "data": {"body": b, "score": s}} for b, s in bodies]
    return [
        {"kind": "Listing", "data": {"children": []}},
        {"kind": "Listing", "data": {"children": children}},
    ]


@pytest.mark.asyncio
async def test_successful_response_returns_three_posts(httpx_mock: HTTPXMock, mocker) -> None:
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    httpx_mock.add_response(
        json=_listing(_post("P1", 100, "id1"), _post("P2", 50, "id2"), _post("P3", 10, "id3"))
    )
    httpx_mock.add_response(json=_comments(("Great", 42)))
    httpx_mock.add_response(json=_comments(("Good", 20)))
    httpx_mock.add_response(json=_comments(("OK", 5)))

    posts = await search_reddit("test")

    assert len(posts) == 3
    assert posts[0]["title"] == "P1"
    assert posts[0]["score"] == 100
    assert "subreddit" in posts[0]
    assert "selftext_preview" in posts[0]
    assert isinstance(posts[0]["top_comments"], list)


@pytest.mark.asyncio
async def test_post_with_low_score_excluded(httpx_mock: HTTPXMock, mocker) -> None:
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    low = _post("Low", score=3, post_id="low1")
    high = _post("High", score=100, post_id="hi1")
    httpx_mock.add_response(json=_listing(low, high))
    httpx_mock.add_response(json=_comments(("Nice", 10)))

    posts = await search_reddit("test")

    assert len(posts) == 1
    assert posts[0]["title"] == "High"


@pytest.mark.asyncio
async def test_429_triggers_retry_succeeds_on_second(httpx_mock: HTTPXMock, mocker) -> None:
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "1"})
    httpx_mock.add_response(json=_listing(_post()))
    httpx_mock.add_response(json=_comments())

    posts = await search_reddit("test")

    assert len(posts) == 1


@pytest.mark.asyncio
async def test_three_consecutive_failures_raise_reddit_unavailable(
    httpx_mock: HTTPXMock, mocker
) -> None:
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)

    with pytest.raises(RedditUnavailableError):
        await search_reddit("test")


@pytest.mark.asyncio
async def test_user_agent_header_present(httpx_mock: HTTPXMock, mocker) -> None:
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    httpx_mock.add_response(json=_listing())

    await search_reddit("test")

    request = httpx_mock.get_requests()[0]
    assert "Mozilla/5.0" in request.headers["User-Agent"]


@pytest.mark.asyncio
async def test_raw_json_param_present(httpx_mock: HTTPXMock, mocker) -> None:
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    httpx_mock.add_response(json=_listing())

    await search_reddit("test")

    request = httpx_mock.get_requests()[0]
    assert "raw_json=1" in str(request.url)


@pytest.mark.asyncio
async def test_deduplication_across_subreddits(httpx_mock: HTTPXMock, mocker) -> None:
    mocker.patch("weles.tools.reddit.asyncio.sleep")
    same_post = _post("Shared Post", score=100, post_id="shared1")
    httpx_mock.add_response(json=_listing(same_post))  # sub1
    httpx_mock.add_response(json=_listing(same_post))  # sub2
    httpx_mock.add_response(json=_comments(("Top comment", 5)))  # comments for the one post

    posts = await search_reddit("test", subreddits=["sub1", "sub2"])

    assert len(posts) == 1
