from weles.research.credibility import score_result, score_results
from weles.tools.reddit import RedditPost
from weles.tools.web import WebResult


def _reddit(score: int, body: str = "") -> RedditPost:
    return RedditPost(
        title="test",
        url="https://reddit.com/r/test/comments/abc",
        score=score,
        created_utc=0.0,
        subreddit="test",
        selftext_preview=body,
        top_comments=[],
    )


def _web(source_type: str = "unknown", url: str = "https://example.com") -> WebResult:
    return WebResult(
        title="test",
        url=url,
        snippet="test snippet about this product",
        domain="example.com",
        source_type=source_type,
    )


def test_reddit_score_50_medium():
    assert score_result(_reddit(50)) == "medium"


def test_reddit_score_150_high():
    assert score_result(_reddit(150)) == "high"


def test_reddit_score_50_ownership_promotes_to_high():
    body = "I have owned this for 3 years and it still works great"
    assert score_result(_reddit(50, body)) == "high"


def test_web_community_high():
    assert score_result(_web("community")) == "high"


def test_web_affiliate_url_flagged():
    assert score_result(_web(url="https://example.com/product?ref=affiliate123")) == "flagged"


def test_batch_flag_three_low_with_shared_ngram():
    body = "this is a great product that everyone should buy today"
    results = [_reddit(10, body), _reddit(15, body), _reddit(8, body)]
    out = score_results(results)
    assert out.get("batch_flag") == "coordinated_positivity"


def test_batch_flag_two_low_no_flag():
    body = "this is a great product that everyone should buy today"
    results = [_reddit(10, body), _reddit(15, body)]
    out = score_results(results)
    assert "batch_flag" not in out


def test_promotion_capped_at_high():
    # score ≥ 100 → high; ownership + switched both try to promote → stays high
    body = "I have owned this for 5 years and switched from the competitor"
    assert score_result(_reddit(150, body)) == "high"
