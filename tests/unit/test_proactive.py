"""Unit tests for run_proactive_checks (issue #31)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from weles.api.session_start import run_proactive_checks
from weles.profile.models import UserProfile


def _insert_history(
    conn,
    item_name: str,
    domain: str,
    status: str,
    item_id: str | None = None,
) -> str:
    iid = item_id or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO history (id, item_name, category, domain, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (iid, item_name, "gear", domain, status, datetime.utcnow()),
    )
    conn.commit()
    return iid


def _empty_profile() -> UserProfile:
    return UserProfile()


# ---------------------------------------------------------------------------
# proactive_surfacing="false" guard
# ---------------------------------------------------------------------------


async def test_proactive_disabled_returns_empty(tmp_db) -> None:
    """Returns [] immediately when proactive_surfacing is 'false'."""
    from weles.db.connection import get_db
    from weles.db.settings_repo import set_setting

    conn = get_db()
    set_setting("proactive_surfacing", "false")
    _insert_history(conn, "Garmin Watch", "shopping", "bought")

    result = await run_proactive_checks(conn, _empty_profile())
    assert result == []


# ---------------------------------------------------------------------------
# QC cache behaviour
# ---------------------------------------------------------------------------


async def test_qc_cache_hit_skips_search(tmp_db, mocker) -> None:
    """When a fresh cache entry exists (< 24 h), search_reddit is not called."""
    from weles.db.connection import get_db
    from weles.db.settings_repo import set_setting

    mock_search = mocker.patch("weles.tools.reddit.search_reddit", return_value=[])

    conn = get_db()
    iid = _insert_history(conn, "Merino Wool Tee", "shopping", "bought")
    # Write a cache entry timestamped 1 hour ago (within 24 h window).
    recent_ts = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    set_setting(f"qc_cache_{iid}", {"timestamp": recent_ts, "found": False})

    await run_proactive_checks(conn, _empty_profile())

    mock_search.assert_not_called()


async def test_qc_cache_miss_calls_search(tmp_db, mocker) -> None:
    """When no cache entry exists, search_reddit is called for the item."""
    from weles.db.connection import get_db

    mock_search = mocker.patch("weles.tools.reddit.search_reddit", return_value=[])

    conn = get_db()
    _insert_history(conn, "Trail Shoes", "shopping", "bought")

    await run_proactive_checks(conn, _empty_profile())

    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args
    assert "Trail Shoes" in call_kwargs.kwargs.get("query", "") or "Trail Shoes" in str(
        call_kwargs.args
    )


async def test_qc_high_score_post_adds_notice(tmp_db, mocker) -> None:
    """A post with score > 50 triggers a QC notice."""
    from weles.db.connection import get_db

    fake_post = {
        "title": "Quality issues with Trail Shoes",
        "url": "https://reddit.com/r/running/comments/abc",
        "score": 99,
        "created_utc": 0.0,
        "subreddit": "running",
        "selftext_preview": "",
        "top_comments": [],
    }
    mocker.patch("weles.tools.reddit.search_reddit", return_value=[fake_post])

    conn = get_db()
    _insert_history(conn, "Trail Shoes", "shopping", "bought")

    notices = await run_proactive_checks(conn, _empty_profile())

    assert len(notices) >= 1
    assert "Trail Shoes" in notices[0]
    assert "https://reddit.com/r/running/comments/abc" in notices[0]


async def test_qc_low_score_post_no_notice(tmp_db, mocker) -> None:
    """A post with score ≤ 50 does not trigger a notice."""
    from weles.db.connection import get_db

    fake_post = {
        "title": "Minor issue with Trail Shoes",
        "url": "https://reddit.com/r/running/comments/xyz",
        "score": 10,
        "created_utc": 0.0,
        "subreddit": "running",
        "selftext_preview": "",
        "top_comments": [],
    }
    mocker.patch("weles.tools.reddit.search_reddit", return_value=[fake_post])

    conn = get_db()
    _insert_history(conn, "Trail Shoes", "shopping", "bought")

    notices = await run_proactive_checks(conn, _empty_profile())

    assert notices == []


async def test_qc_only_first_5_items_checked(tmp_db, mocker) -> None:
    """Only the 5 most recent bought/tried items are checked."""
    from weles.db.connection import get_db

    mock_search = mocker.patch("weles.tools.reddit.search_reddit", return_value=[])

    conn = get_db()
    for i in range(7):
        _insert_history(conn, f"Item {i}", "shopping", "bought")

    await run_proactive_checks(conn, _empty_profile())

    assert mock_search.call_count == 5


# ---------------------------------------------------------------------------
# Seasonal surfacing
# ---------------------------------------------------------------------------


async def test_seasonal_match_with_domain_history_adds_notice(tmp_db, mocker) -> None:
    """Seasonal entry for current month + user has domain history → notice returned."""
    from weles.db.connection import get_db

    mocker.patch("weles.tools.reddit.search_reddit", return_value=[])

    current_month = datetime.utcnow().month
    fake_seasonal = {
        "entries": [
            {
                "domain": "fitness",
                "months": [current_month],
                "prompt": "Time to review your training plan.",
            }
        ]
    }
    mocker.patch("weles.api.session_start.tomllib.load", return_value=fake_seasonal)  # type: ignore[attr-defined]

    conn = get_db()
    _insert_history(conn, "Barbell", "fitness", "bought")

    notices = await run_proactive_checks(conn, _empty_profile())

    assert "Time to review your training plan." in notices


async def test_seasonal_match_without_domain_history_no_notice(tmp_db, mocker) -> None:
    """Seasonal entry for current month + user has no domain history → no notice."""
    from weles.db.connection import get_db

    mocker.patch("weles.tools.reddit.search_reddit", return_value=[])

    current_month = datetime.utcnow().month
    fake_seasonal = {
        "entries": [
            {
                "domain": "fitness",
                "months": [current_month],
                "prompt": "Time to review your training plan.",
            }
        ]
    }
    mocker.patch("weles.api.session_start.tomllib.load", return_value=fake_seasonal)  # type: ignore[attr-defined]

    conn = get_db()
    # Insert history in a *different* domain
    _insert_history(conn, "Chicken Breast", "diet", "bought")

    notices = await run_proactive_checks(conn, _empty_profile())

    assert "Time to review your training plan." not in notices


async def test_seasonal_wrong_month_no_notice(tmp_db, mocker) -> None:
    """Seasonal entry for a different month produces no notice."""
    from weles.db.connection import get_db

    mocker.patch("weles.tools.reddit.search_reddit", return_value=[])

    current_month = datetime.utcnow().month
    other_month = (current_month % 12) + 1  # always a different month
    fake_seasonal = {
        "entries": [
            {
                "domain": "fitness",
                "months": [other_month],
                "prompt": "This should not appear.",
            }
        ]
    }
    mocker.patch("weles.api.session_start.tomllib.load", return_value=fake_seasonal)  # type: ignore[attr-defined]

    conn = get_db()
    _insert_history(conn, "Barbell", "fitness", "bought")

    notices = await run_proactive_checks(conn, _empty_profile())

    assert "This should not appear." not in notices
