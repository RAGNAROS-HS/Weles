from unittest.mock import AsyncMock, patch

import pytest

from weles.agent.dispatch import ToolResult
from weles.api.routers.messages import make_search_reddit_handler


@pytest.fixture
def mock_search_reddit_handler():
    result = ToolResult(summary="Found 3 posts (top score: 100)", data=[])
    with patch(
        "weles.api.routers.messages.search_reddit_handler",
        new_callable=AsyncMock,
        return_value=result,
    ) as m:
        yield m


async def test_no_subreddits_injects_general_defaults(mock_search_reddit_handler):
    handler = make_search_reddit_handler("fitness")
    await handler({"query": "protein intake"})
    called_input = mock_search_reddit_handler.call_args[0][0]
    assert called_input["subreddits"] == ["Fitness", "weightroom", "bodyweightfitness"]


async def test_subcategory_resolves_to_specific_subreddits(mock_search_reddit_handler):
    handler = make_search_reddit_handler("fitness")
    await handler({"query": "marathon training", "subcategory": "running"})
    called_input = mock_search_reddit_handler.call_args[0][0]
    assert called_input["subreddits"] == ["running", "trailrunning", "BuyItForLife"]


async def test_explicit_subreddits_not_overridden(mock_search_reddit_handler):
    handler = make_search_reddit_handler("fitness")
    await handler({"query": "creatine", "subreddits": ["bodybuilding"]})
    called_input = mock_search_reddit_handler.call_args[0][0]
    assert called_input["subreddits"] == ["bodybuilding"]


async def test_general_mode_falls_back_to_buyitforlife(mock_search_reddit_handler):
    handler = make_search_reddit_handler("general")
    await handler({"query": "best headphones"})
    called_input = mock_search_reddit_handler.call_args[0][0]
    assert called_input["subreddits"] == ["BuyItForLife"]
