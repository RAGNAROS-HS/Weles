import json


def test_sse_content_type(client, mock_claude):
    session_id = client.post("/sessions").json()["id"]
    with client.stream(
        "POST", f"/sessions/{session_id}/messages", json={"content": "Hello"}
    ) as resp:
        assert "text/event-stream" in resp.headers["content-type"]


def test_sse_includes_text_delta_and_done(client, mock_claude):
    session_id = client.post("/sessions").json()["id"]
    events = []
    with client.stream(
        "POST", f"/sessions/{session_id}/messages", json={"content": "Hello"}
    ) as resp:
        for line in resp.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())

    assert "text_delta" in events
    assert "done" in events


def test_sse_done_title_equals_first_50_chars(client, mock_claude):
    session_id = client.post("/sessions").json()["id"]
    content = "A" * 60
    done_data = None
    with client.stream(
        "POST", f"/sessions/{session_id}/messages", json={"content": content}
    ) as resp:
        current_event = None
        for line in resp.iter_lines():
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and current_event == "done":
                done_data = json.loads(line.split(":", 1)[1].strip())

    assert done_data is not None
    assert done_data["title"] == content[:50]
