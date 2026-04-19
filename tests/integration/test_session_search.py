"""Integration tests: GET /sessions?search= param."""


def test_search_filters_by_title(client) -> None:
    from weles.db.connection import get_db

    conn = get_db()
    # Create two sessions with known titles
    r1 = client.post("/sessions")
    r2 = client.post("/sessions")
    sid1, sid2 = r1.json()["id"], r2.json()["id"]
    conn.execute("UPDATE sessions SET title = ? WHERE id = ?", ("Running shoes advice", sid1))
    conn.execute("UPDATE sessions SET title = ? WHERE id = ?", ("Diet plan", sid2))
    conn.commit()

    r = client.get("/sessions?search=running")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert sid1 in ids
    assert sid2 not in ids


def test_search_is_case_insensitive(client) -> None:
    from weles.db.connection import get_db

    conn = get_db()
    r1 = client.post("/sessions")
    sid1 = r1.json()["id"]
    conn.execute("UPDATE sessions SET title = ? WHERE id = ?", ("Running shoes advice", sid1))
    conn.commit()

    r = client.get("/sessions?search=RUNNING")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert sid1 in ids


def test_empty_search_returns_all(client) -> None:
    client.post("/sessions")
    client.post("/sessions")

    r_all = client.get("/sessions")
    r_empty = client.get("/sessions?search=")
    assert r_all.status_code == 200
    assert r_empty.status_code == 200
    assert len(r_all.json()) == len(r_empty.json())


def test_search_excludes_null_titles(client) -> None:
    # A brand-new session has title=null; it should not appear in search results
    client.post("/sessions")
    r = client.get("/sessions?search=new")
    assert r.status_code == 200
    for s in r.json():
        assert s["title"] is not None
