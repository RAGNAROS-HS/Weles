"""Integration tests: mode switch system note injection."""


def test_mode_switch_note_injected_in_user_turn(client, mock_claude) -> None:
    session = client.post("/sessions").json()
    sid = session["id"]

    # First message in general mode (no note)
    client.post(
        f"/sessions/{sid}/messages",
        json={"content": "Hello"},
        headers={"Accept": "text/event-stream"},
    )

    # Patch to diet mode
    client.patch(f"/sessions/{sid}", json={"mode": "diet"})

    # Second message with mode_changed_to
    client.post(
        f"/sessions/{sid}/messages",
        json={"content": "What should I eat?", "mode_changed_to": "diet"},
        headers={"Accept": "text/event-stream"},
    )

    # Fetch messages from DB via API
    msgs = client.get(f"/sessions/{sid}/messages").json()
    user_messages = [m for m in msgs if m["role"] == "user"]
    assert len(user_messages) == 2

    second_user = user_messages[1]["content"]
    assert "[System: Mode changed to diet]" in second_user
    assert "What should I eat?" in second_user


def test_no_mode_switch_note_when_field_absent(client, mock_claude) -> None:
    session = client.post("/sessions").json()
    sid = session["id"]

    client.post(
        f"/sessions/{sid}/messages",
        json={"content": "Hello"},
        headers={"Accept": "text/event-stream"},
    )

    msgs = client.get(f"/sessions/{sid}/messages").json()
    user_messages = [m for m in msgs if m["role"] == "user"]
    assert "[System: Mode changed to" not in user_messages[0]["content"]
