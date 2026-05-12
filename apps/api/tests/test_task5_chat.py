"""Task 5 tests: Chat session, streaming, lifecycle, and message status."""

from __future__ import annotations

import json


def create_workspace(client, name: str = "Chat Workspace") -> dict:
    response = client.post("/workspaces", json={"name": name, "description": "Chat test workspace"})
    assert response.status_code == 201
    return response.json()


def parse_sse_events(response) -> list[dict]:
    """Parse SSE response into list of event dicts. Returns list of parsed JSON or '[DONE]'."""
    events: list[dict] = []
    for line in response.text.split("\n"):
        line = line.strip()
        if not line or not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload == "[DONE]":
            events.append({"type": "[DONE]"})
        else:
            events.append(json.loads(payload))
    return events


# ---------------------------------------------------------------------------
# Legacy non-streaming tests (kept for backward compatibility)
# ---------------------------------------------------------------------------

def test_create_chat_session(client) -> None:
    workspace = create_workspace(client)

    response = client.post("/chat/sessions", json={"workspace_id": workspace["id"], "title": "Market strategy"})

    assert response.status_code == 201, response.text
    assert response.json()["workspace_id"] == workspace["id"]
    assert response.json()["title"] == "Market strategy"


def test_list_chat_sessions_scoped_by_workspace(client) -> None:
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")
    first_session = client.post("/chat/sessions", json={"workspace_id": first["id"], "title": "A chat"}).json()
    client.post("/chat/sessions", json={"workspace_id": second["id"], "title": "B chat"})

    response = client.get(f"/chat/sessions?workspace_id={first['id']}")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [first_session["id"]]


def test_send_message_creates_user_and_assistant_messages(client) -> None:
    workspace = create_workspace(client)
    chat_session = client.post("/chat/sessions", json={"workspace_id": workspace["id"]}).json()

    response = client.post(
        f"/chat/sessions/{chat_session['id']}/messages?workspace_id={workspace['id']}",
        json={"content": "What should we do next quarter?"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["user_message"]["role"] == "user"
    assert payload["user_message"]["content"] == "What should we do next quarter?"
    assert payload["assistant_message"]["role"] == "assistant"
    assert "placeholder" in payload["assistant_message"]["content"].lower()


def test_get_chat_session_returns_messages(client) -> None:
    workspace = create_workspace(client)
    chat_session = client.post("/chat/sessions", json={"workspace_id": workspace["id"]}).json()
    client.post(f"/chat/sessions/{chat_session['id']}/messages?workspace_id={workspace['id']}", json={"content": "Analyze churn risk"})

    response = client.get(f"/chat/sessions/{chat_session['id']}?workspace_id={workspace['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == workspace["id"]
    assert payload["title"] == "Analyze churn risk"
    assert [message["role"] for message in payload["messages"]] == ["user", "assistant"]


def test_send_empty_message_is_rejected(client) -> None:
    workspace = create_workspace(client)
    chat_session = client.post("/chat/sessions", json={"workspace_id": workspace["id"]}).json()

    response = client.post(f"/chat/sessions/{chat_session['id']}/messages?workspace_id={workspace['id']}", json={"content": "   "})

    assert response.status_code == 400


def test_chat_session_detail_rejects_wrong_workspace(client) -> None:
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")
    chat_session = client.post("/chat/sessions", json={"workspace_id": first["id"]}).json()

    response = client.get(f"/chat/sessions/{chat_session['id']}?workspace_id={second['id']}")

    assert response.status_code == 404


def test_send_message_rejects_wrong_workspace(client) -> None:
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")
    chat_session = client.post("/chat/sessions", json={"workspace_id": first["id"]}).json()

    response = client.post(
        f"/chat/sessions/{chat_session['id']}/messages?workspace_id={second['id']}",
        json={"content": "Should not persist"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Streaming / SSE tests
# ---------------------------------------------------------------------------

def test_stream_first_message_lazily_creates_session(client) -> None:
    """POST /chat/messages/stream without session_id → session_created event + new session."""
    workspace = create_workspace(client)

    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "Hello streaming"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = parse_sse_events(response)
    types = [e["type"] for e in events]

    assert "session_created" in types
    assert "user_message_saved" in types
    assert "assistant_started" in types
    assert "text_delta" in types
    assert "assistant_completed" in types
    assert "[DONE]" in types

    # session_created event should contain session data
    session_event = next(e for e in events if e["type"] == "session_created")
    assert session_event["session"]["workspace_id"] == workspace["id"]
    assert session_event["session"]["id"] is not None

    # Title starts as default; gets updated after user message is saved
    # Check the final title via the session detail endpoint
    session_id = session_event["session"]["id"]
    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    assert detail["title"] != "New Chat"
    assert detail["title"] == "Hello streaming"


def test_stream_existing_session_continuation(client) -> None:
    """POST /chat/messages/stream with session_id continues existing session."""
    workspace = create_workspace(client)

    # First stream creates session
    r1 = client.post("/chat/messages/stream", json={"workspace_id": workspace["id"], "message": "First message"})
    events1 = parse_sse_events(r1)
    session_event = next(e for e in events1 if e["type"] == "session_created")
    session_id = session_event["session"]["id"]

    # Second stream continues
    r2 = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "session_id": session_id, "message": "Second message"},
    )

    assert r2.status_code == 200
    events2 = parse_sse_events(r2)
    types2 = [e["type"] for e in events2]

    # No session_created since we provided session_id
    assert "session_created" not in types2
    assert "user_message_saved" in types2
    assert "assistant_completed" in types2
    assert "[DONE]" in types2


def test_stream_wrong_workspace_rejection(client) -> None:
    """Stream with session_id belonging to different workspace → error event."""
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")

    # Create session in first workspace
    r1 = client.post("/chat/messages/stream", json={"workspace_id": first["id"], "message": "Hello"})
    events1 = parse_sse_events(r1)
    session_event = next(e for e in events1 if e["type"] == "session_created")
    session_id = session_event["session"]["id"]

    # Try to use from second workspace
    r2 = client.post(
        "/chat/messages/stream",
        json={"workspace_id": second["id"], "session_id": session_id, "message": "Intruder"},
    )

    events2 = parse_sse_events(r2)
    types2 = [e["type"] for e in events2]
    assert "error" in types2


def test_stream_events_parse_as_data_json_and_done(client) -> None:
    """All SSE events are parseable JSON with 'type', ending with data: [DONE]."""
    workspace = create_workspace(client)

    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "Parse check"},
    )

    assert response.status_code == 200
    events = parse_sse_events(response)

    # Every non-DONE event must be a dict with 'type'
    for event in events:
        assert "type" in event

    # Last event is [DONE]
    assert events[-1]["type"] == "[DONE]"


def test_stream_message_status_transitions_to_completed(client) -> None:
    """After stream completes, assistant message status is 'completed'."""
    workspace = create_workspace(client)

    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "Status check"},
    )

    events = parse_sse_events(response)
    completed_event = next(e for e in events if e["type"] == "assistant_completed")
    msg = completed_event["message"]

    assert msg["status"] == "completed"
    assert msg["completed_at"] is not None
    assert msg["content"] != ""

    # User message should also be completed
    user_event = next(e for e in events if e["type"] == "user_message_saved")
    assert user_event["message"]["status"] == "completed"


def test_stream_empty_message_returns_error(client) -> None:
    """Empty message in stream → error event, no session created."""
    workspace = create_workspace(client)

    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "   "},
    )

    events = parse_sse_events(response)
    types = [e["type"] for e in events]
    assert "error" in types


def test_stream_nonexistent_workspace_returns_error(client) -> None:
    """Workspace 999999 doesn't exist → error event."""
    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": 999999, "message": "Oops"},
    )

    events = parse_sse_events(response)
    types = [e["type"] for e in events]
    assert "error" in types


# ---------------------------------------------------------------------------
# Session pagination & summary fields
# ---------------------------------------------------------------------------

def test_list_sessions_pagination_default_limit(client) -> None:
    """GET /chat/sessions defaults to limit=5."""
    workspace = create_workspace(client)

    # Create 7 sessions
    for i in range(7):
        client.post("/chat/sessions", json={"workspace_id": workspace["id"], "title": f"Chat {i}"})

    response = client.get(f"/chat/sessions?workspace_id={workspace['id']}")
    assert response.status_code == 200
    assert len(response.json()) == 5

    # Offset by 5 should return remaining 2
    response2 = client.get(f"/chat/sessions?workspace_id={workspace['id']}&offset=5")
    assert response2.status_code == 200
    assert len(response2.json()) == 2


def test_list_sessions_pagination_custom_limit(client) -> None:
    """GET /chat/sessions respects custom limit."""
    workspace = create_workspace(client)
    for i in range(4):
        client.post("/chat/sessions", json={"workspace_id": workspace["id"], "title": f"Chat {i}"})

    response = client.get(f"/chat/sessions?workspace_id={workspace['id']}&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_session_summary_fields_present(client) -> None:
    """Session detail and list responses include summary fields."""
    workspace = create_workspace(client)
    session_resp = client.post("/chat/sessions", json={"workspace_id": workspace["id"], "title": "Summary test"})
    session_data = session_resp.json()

    # List endpoint
    list_resp = client.get(f"/chat/sessions?workspace_id={workspace['id']}")
    item = next(s for s in list_resp.json() if s["id"] == session_data["id"])
    for field in ("last_message_at", "conversation_summary", "summary_cutoff_message_id", "summary_updated_at"):
        assert field in item, f"Missing field {field} in list response"

    # Detail endpoint
    detail_resp = client.get(f"/chat/sessions/{session_data['id']}?workspace_id={workspace['id']}")
    detail = detail_resp.json()
    for field in ("last_message_at", "conversation_summary", "summary_cutoff_message_id", "summary_updated_at"):
        assert field in detail, f"Missing field {field} in detail response"


def test_message_lifecycle_fields_in_detail(client) -> None:
    """Messages in session detail include status, updated_at, completed_at."""
    workspace = create_workspace(client)

    # Send via stream to get lifecycle fields
    client.post("/chat/messages/stream", json={"workspace_id": workspace["id"], "message": "Lifecycle test"})

    # Get sessions to find the one just created
    sessions_resp = client.get(f"/chat/sessions?workspace_id={workspace['id']}")
    session_id = sessions_resp.json()[0]["id"]

    detail_resp = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}")
    messages = detail_resp.json()["messages"]

    for msg in messages:
        assert "status" in msg
        assert "updated_at" in msg
        assert "completed_at" in msg
        assert msg["status"] == "completed"


def test_stream_updates_last_message_at(client) -> None:
    """After streaming, session.last_message_at is set."""
    workspace = create_workspace(client)

    client.post("/chat/messages/stream", json={"workspace_id": workspace["id"], "message": "Timestamp check"})

    sessions_resp = client.get(f"/chat/sessions?workspace_id={workspace['id']}")
    session_data = sessions_resp.json()[0]
    assert session_data["last_message_at"] is not None


# ---------------------------------------------------------------------------
# Context builder: session continuity tests
# ---------------------------------------------------------------------------

def _send_stream_turns(client, workspace_id: int, session_id: int | None, count: int) -> tuple[int, list[dict]]:
    """Send *count* streaming turns, return (session_id, all events)."""
    sid = session_id
    all_events: list[dict] = []
    for i in range(count):
        r = client.post(
            "/chat/messages/stream",
            json={"workspace_id": workspace_id, "session_id": sid, "message": f"Turn {i}"},
        )
        assert r.status_code == 200, r.text
        events = parse_sse_events(r)
        all_events.extend(events)
        if sid is None:
            created = next(e for e in events if e["type"] == "session_created")
            sid = created["session"]["id"]
    return sid, all_events


def test_short_session_context_all_messages_raw_no_summary(client) -> None:
    """Short session (≤10 messages): all messages returned raw, no summary generated."""
    workspace = create_workspace(client)
    session_id, _ = _send_stream_turns(client, workspace["id"], None, 3)

    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    # 3 turns = 6 messages (user + assistant each)
    assert len(detail["messages"]) == 6
    # No summary needed for short sessions
    assert detail["conversation_summary"] is None
    assert detail["summary_cutoff_message_id"] is None
    assert detail["summary_updated_at"] is None


def test_long_session_refreshes_summary_and_cutoff(client) -> None:
    """Long session (>10 messages): summary is created with cutoff + recent raw kept."""
    workspace = create_workspace(client)
    # 7 turns = 14 messages (each turn = 1 user + 1 assistant), then send one more = 16 total
    session_id, _ = _send_stream_turns(client, workspace["id"], None, 7)
    # One more turn to trigger summary (16 total > 10 window)
    _send_stream_turns(client, workspace["id"], session_id, 1)

    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    total_msgs = len(detail["messages"])
    assert total_msgs == 16

    # Summary should now exist
    assert detail["conversation_summary"] is not None
    assert len(detail["conversation_summary"]) > 0
    assert detail["summary_cutoff_message_id"] is not None
    assert detail["summary_updated_at"] is not None

    # Summary should contain role-prefixed lines for older messages
    summary_lines = detail["conversation_summary"].strip().split("\n")
    assert len(summary_lines) > 0
    # First line should start with a role prefix
    assert summary_lines[0].startswith("user:") or summary_lines[0].startswith("assistant:")


def test_stream_path_triggers_summary_state_when_enough_messages(client) -> None:
    """Streaming path populates summary fields after session grows past the window."""
    workspace = create_workspace(client)
    # 6 turns = 12 messages; that crosses the 10-message default window
    session_id, _ = _send_stream_turns(client, workspace["id"], None, 6)

    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    assert detail["conversation_summary"] is not None
    assert detail["summary_cutoff_message_id"] is not None
    assert detail["summary_updated_at"] is not None

    # Verify summary_updated_at is a valid ISO timestamp
    from datetime import datetime
    datetime.fromisoformat(detail["summary_updated_at"])


def test_long_session_keeps_recent_raw_messages(client) -> None:
    """Long session: context keeps exactly the recent window of raw messages."""
    workspace = create_workspace(client)
    # 7 turns = 14 messages, then 1 more = 16 total
    session_id, _ = _send_stream_turns(client, workspace["id"], None, 8)

    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    total_msgs = len(detail["messages"])
    assert total_msgs > 10

    # The summary should cover older messages (cutoff_message_id < newest message id)
    assert detail["summary_cutoff_message_id"] < detail["messages"][-1]["id"]

    # Summary lines should correspond to messages before cutoff
    cutoff_id = detail["summary_cutoff_message_id"]
    older_msgs = [m for m in detail["messages"] if m["id"] <= cutoff_id]
    summary_lines = detail["conversation_summary"].strip().split("\n")
    # There should be roughly one line per older message (some may merge at char limit)
    assert len(summary_lines) <= len(older_msgs)


def test_summary_updates_as_session_grows(client) -> None:
    """Summary cutoff advances as more messages are added past the window."""
    workspace = create_workspace(client)
    # 6 turns = 12 messages → first summary
    session_id, _ = _send_stream_turns(client, workspace["id"], None, 6)

    detail1 = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    first_cutoff = detail1["summary_cutoff_message_id"]

    # Add 2 more turns = 16 messages → summary should advance
    _send_stream_turns(client, workspace["id"], session_id, 2)

    detail2 = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    second_cutoff = detail2["summary_cutoff_message_id"]

    assert second_cutoff > first_cutoff
