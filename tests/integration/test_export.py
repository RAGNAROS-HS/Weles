"""Integration tests: GET /export endpoint."""

import io
import zipfile


def test_json_export_returns_200_with_disposition(client) -> None:
    r = client.get("/export")
    assert r.status_code == 200
    assert "weles-export" in r.headers.get("content-disposition", "")


def test_json_export_body_has_required_keys(client) -> None:
    r = client.get("/export")
    assert r.status_code == 200
    data = r.json()
    assert "profile" in data
    assert "preferences" in data
    assert "history" in data
    assert "exported_at" in data


def test_csv_export_returns_zip(client) -> None:
    r = client.get("/export?format=csv")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip")


def test_csv_export_zip_contains_three_files(client) -> None:
    r = client.get("/export?format=csv")
    assert r.status_code == 200
    buf = io.BytesIO(r.content)
    with zipfile.ZipFile(buf) as zf:
        names = set(zf.namelist())
    assert names == {"profile.csv", "preferences.csv", "history.csv"}
