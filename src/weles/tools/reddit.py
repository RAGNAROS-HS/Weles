import asyncio
from typing import Any, TypedDict

import httpx

from weles.agent.dispatch import ToolResult
from weles.utils.errors import RedditUnavailableError

_SEMAPHORE = asyncio.Semaphore(1)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}
_MAX_RETRIES = 3
_BASE = "https://www.reddit.com"


class RedditPost(TypedDict):
    title: str
    url: str
    score: int
    created_utc: float
    subreddit: str
    selftext_preview: str
    top_comments: list[dict[str, Any]]


async def _reddit_get(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> Any:
    """Single URL fetch with rate-limit semaphore, 1 s sleep, and 429 backoff."""
    for attempt in range(_MAX_RETRIES):
        async with _SEMAPHORE:
            try:
                resp = await client.get(url, params=params)
            except httpx.RequestError as exc:
                await asyncio.sleep(1.0)
                if attempt == _MAX_RETRIES - 1:
                    raise RedditUnavailableError(str(exc)) from exc
                continue

            await asyncio.sleep(1.0)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "10"))
            await asyncio.sleep(retry_after)
            continue

        if resp.is_success:
            return resp.json()

        if attempt == _MAX_RETRIES - 1:
            raise RedditUnavailableError(f"HTTP {resp.status_code} from {url}")

    raise RedditUnavailableError(f"Reddit unavailable after {_MAX_RETRIES} attempts")


def _parse_posts(data: dict[str, Any]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        score = d.get("score", 0)
        if score < 5:
            continue
        posts.append(
            {
                "title": d.get("title", ""),
                "url": _BASE + d.get("permalink", d.get("url", "")),
                "score": score,
                "created_utc": float(d.get("created_utc", 0)),
                "subreddit": d.get("subreddit", ""),
                "selftext_preview": (d.get("selftext", "") or "")[:500],
                "top_comments": [],
                "_id": d.get("id", ""),
                "_subreddit": d.get("subreddit", ""),
            }
        )
    return posts


def _parse_comments(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list) or len(data) < 2:
        return []
    children = data[1].get("data", {}).get("children", [])
    comments: list[dict[str, Any]] = []
    for child in children:
        if child.get("kind") != "t1":
            continue
        d = child.get("data", {})
        comments.append({"body": d.get("body", ""), "score": d.get("score", 0)})
    comments.sort(key=lambda c: c["score"], reverse=True)
    return comments[:3]


async def _fetch_comments(
    client: httpx.AsyncClient, posts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for post in posts:
        sub = post.get("_subreddit", "")
        pid = post.get("_id", "")
        if sub and pid:
            try:
                url = f"{_BASE}/r/{sub}/comments/{pid}.json"
                data = await _reddit_get(client, url, {"limit": "5", "depth": "1", "raw_json": "1"})
                comments = _parse_comments(data)
            except (RedditUnavailableError, Exception):
                comments = []
        else:
            comments = []
        clean = {k: v for k, v in post.items() if not k.startswith("_")}
        results.append({**clean, "top_comments": comments})
    return results


async def search_reddit(
    query: str,
    subreddits: list[str] | None = None,
    limit: int = 10,
    sort: str = "relevance",
    time_filter: str = "year",
) -> list[RedditPost]:
    base_params: dict[str, Any] = {
        "q": query,
        "sort": sort,
        "t": time_filter,
        "limit": str(limit),
        "raw_json": "1",
    }

    async with httpx.AsyncClient(headers=_HEADERS) as client:
        if subreddits:
            seen_urls: set[str] = set()
            extended: list[dict[str, Any]] = []
            for sub in subreddits:
                url = f"{_BASE}/r/{sub}/search.json"
                data = await _reddit_get(client, url, {**base_params, "restrict_sr": "true"})
                for post in _parse_posts(data):
                    if post["url"] not in seen_urls:
                        seen_urls.add(post["url"])
                        extended.append(post)
        else:
            url = f"{_BASE}/search.json"
            data = await _reddit_get(client, url, base_params)
            extended = _parse_posts(data)

        results = await _fetch_comments(client, extended)

    results.sort(key=lambda p: p["score"], reverse=True)
    return results  # type: ignore[return-value]


SEARCH_REDDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query."},
        "subcategory": {
            "type": "string",
            "description": (
                "Subcategory hint for subreddit routing (e.g. 'footwear', 'running'). "
                "The server resolves this to the appropriate subreddits. "
                "Ignored if subreddits are explicitly provided."
            ),
        },
        "subreddits": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit subreddits to scope the search. Overrides subcategory.",
        },
        "limit": {
            "type": "integer",
            "default": 10,
            "description": "Max posts to return (default 10).",
        },
        "sort": {
            "type": "string",
            "enum": ["relevance", "hot", "top", "new"],
            "default": "relevance",
        },
        "time_filter": {
            "type": "string",
            "enum": ["hour", "day", "week", "month", "year", "all"],
            "default": "year",
        },
    },
    "required": ["query"],
}


async def search_reddit_handler(tool_input: dict[str, Any]) -> ToolResult:
    from weles.research.credibility import score_results

    posts = await search_reddit(
        query=tool_input["query"],
        subreddits=tool_input.get("subreddits"),
        limit=tool_input.get("limit", 10),
        sort=tool_input.get("sort", "relevance"),
        time_filter=tool_input.get("time_filter", "year"),
    )
    if not posts:
        return ToolResult(summary="No posts found.", data=[])
    scored = score_results(posts)
    top_score = posts[0]["score"]
    return ToolResult(
        summary=f"Found {len(scored['results'])} posts (top score: {top_score})",
        data=scored,
    )
