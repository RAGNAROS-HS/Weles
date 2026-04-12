import json

from fastapi.testclient import TestClient


def test_patch_profile_valid_field_returns_200(client: TestClient) -> None:
    resp = client.patch("/profile", json={"fitness_level": "beginner"})
    assert resp.status_code == 200
    assert resp.json()["fitness_level"] == "beginner"


def test_patch_profile_invalid_enum_returns_422(client: TestClient) -> None:
    resp = client.patch("/profile", json={"fitness_level": "invalid"})
    assert resp.status_code == 422


def test_patch_profile_unknown_field_returns_422(client: TestClient) -> None:
    resp = client.patch("/profile", json={"unknown_field": "x"})
    assert resp.status_code == 422


def test_patch_profile_sets_field_timestamp(client: TestClient) -> None:
    client.patch("/profile", json={"fitness_level": "beginner"})
    resp = client.get("/profile")
    timestamps = json.loads(resp.json()["field_timestamps"])
    assert "fitness_level" in timestamps


def test_patch_profile_does_not_set_unwritten_field_timestamp(client: TestClient) -> None:
    client.patch("/profile", json={"fitness_level": "beginner"})
    resp = client.get("/profile")
    timestamps = json.loads(resp.json()["field_timestamps"])
    assert "weight_kg" not in timestamps
