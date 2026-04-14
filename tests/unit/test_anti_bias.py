"""Unit tests for anti-bias and astroturfing heuristics (issue #30)."""

from weles.research.credibility import score_results


def _web_result(url: str, domain: str = "example.com", source_type: str = "unknown") -> dict:
    return {
        "title": "Test",
        "url": url,
        "snippet": "Some text.",
        "domain": domain,
        "source_type": source_type,
    }


def _reddit_post(text: str, score: int = 1) -> dict:
    return {
        "title": "Test post",
        "url": "https://reddit.com/r/test/comments/abc",
        "score": score,
        "created_utc": 0.0,
        "subreddit": "test",
        "selftext_preview": text,
        "top_comments": [],
    }


def test_affiliate_ref_param_flagged_with_metadata() -> None:
    """`?ref=` in URL → credibility 'flagged' and affiliate: True."""
    result = _web_result("https://shop.example.com/product?ref=partner123")
    out = score_results([result])
    scored = out["results"][0]
    assert scored["credibility"] == "flagged"
    assert scored.get("affiliate") is True


def test_affiliate_go_path_flagged() -> None:
    """`/go/` in URL path → credibility 'flagged'."""
    result = _web_result("https://review.example.com/go/some-product")
    out = score_results([result])
    scored = out["results"][0]
    assert scored["credibility"] == "flagged"


def test_non_affiliate_url_unaffected() -> None:
    """Unknown URL with no affiliate params → no 'affiliate' tag, credibility 'medium'."""
    result = _web_result("https://example.com/review")
    out = score_results([result])
    scored = out["results"][0]
    assert scored["credibility"] == "medium"
    assert "affiliate" not in scored


def test_geo_block_tags_available_false(tmp_path, monkeypatch) -> None:
    """Domain in PL.txt + country_code='PL' → available: False."""
    import weles.research.credibility as cred_module

    # Clear cache to avoid cross-test pollution
    cred_module._geo_block_cache.clear()

    # Point resource_path to a temp dir with a PL.txt file
    geo_dir = tmp_path / "config" / "geo_blocks"
    geo_dir.mkdir(parents=True)
    (geo_dir / "PL.txt").write_text("bestbuy.com\nnewegg.com\n")

    import weles.utils.paths as paths_module

    original_resource_path = paths_module.resource_path

    def patched_resource_path(rel: str):
        candidate = tmp_path / rel
        if candidate.exists():
            return candidate
        return original_resource_path(rel)

    monkeypatch.setattr(paths_module, "resource_path", patched_resource_path)
    monkeypatch.setattr(cred_module, "resource_path", patched_resource_path)

    result = _web_result("https://bestbuy.com/product", domain="bestbuy.com")
    out = score_results([result], country_code="PL")
    scored = out["results"][0]
    assert scored.get("available") is False


def test_no_geo_block_file_no_available_tag(tmp_path, monkeypatch) -> None:
    """If no geo_block file exists for the country, no 'available' tag applied."""
    import weles.research.credibility as cred_module

    cred_module._geo_block_cache.clear()

    import weles.utils.paths as paths_module

    original_resource_path = paths_module.resource_path

    def patched_resource_path(rel: str):
        # Never find config/geo_blocks/XX.txt
        if "geo_blocks" in rel:
            return tmp_path / rel
        return original_resource_path(rel)

    monkeypatch.setattr(paths_module, "resource_path", patched_resource_path)
    monkeypatch.setattr(cred_module, "resource_path", patched_resource_path)

    result = _web_result("https://bestbuy.com/product", domain="bestbuy.com")
    out = score_results([result], country_code="XX")
    scored = out["results"][0]
    assert "available" not in scored


def test_coordinated_positivity_via_shared_phrase() -> None:
    """3 low-credibility results with shared phrase → coordinated_positivity."""
    posts = [
        _reddit_post("This product exceeded my expectations, great buy.", score=2),
        _reddit_post("I was amazed — exceeded my expectations by a lot.", score=3),
        _reddit_post("It totally exceeded my expectations, can't fault it.", score=1),
    ]
    out = score_results(posts)
    assert out.get("batch_flag") == "coordinated_positivity"
