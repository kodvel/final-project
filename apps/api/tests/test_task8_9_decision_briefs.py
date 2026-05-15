"""Tasks 8 & 9 tests: Decision Brief Draft generation + approval status actions.

The /decision-brief command runs without a real LLM by leveraging the
deterministic fallback that fires when ``rag_openai_api_key`` is unset (the
default in tests). Approval transitions use the small state machine in
``app/services/decision_briefs.py`` and index the brief into ChromaDB on
approval — we mock the indexing helper to keep tests fast.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from sqlmodel import Session, select

from app.models.chat import ChatMessage, ChatSession, MessageSourceCitation
from app.models.decision_brief import DecisionBrief
from app.models.enums import (
    ChatMessageRole,
    ChatMessageType,
    CitationType,
    DecisionApprovalStatus,
    DecisionRecommendationStatus,
    MessageStatus,
)
from app.services import decision_briefs as decision_brief_service


def _create_workspace(client, name: str = "Brief Workspace") -> dict:
    response = client.post("/workspaces", json={"name": name, "description": "Brief tests"})
    assert response.status_code == 201
    return response.json()


def _parse_sse_events(response) -> list[dict]:
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


def _seed_session_with_citations(
    client,
    workspace_id: int,
    *,
    citations: int = 2,
) -> tuple[int, list[int]]:
    """Build a chat session with an assistant message + N citations."""
    from app.db.session import engine

    # Stream one message to seed a session + user/assistant messages.
    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace_id, "message": "Should we expand to Berlin?"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response)
    session_id = next(e["session_id"] for e in events if e.get("type") == "metadata")

    # Inject citations on the assistant message so brief generation has evidence.
    with Session(engine) as db:
        assistant = db.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .where(ChatMessage.role == ChatMessageRole.ASSISTANT)
        ).first()
        assert assistant is not None
        ordinals: list[int] = []
        for ordinal in range(1, citations + 1):
            db.add(
                MessageSourceCitation(
                    message_id=assistant.id,
                    citation_type=CitationType.UPLOADED_SOURCE,
                    ordinal=ordinal,
                    title=f"Source {ordinal}",
                    quote=f"Evidence #{ordinal}",
                    citation_status="available",
                    retrieved_at=datetime.utcnow(),
                )
            )
            ordinals.append(ordinal)
        db.commit()

    return session_id, ordinals


# ---------------------------------------------------------------------------
# Task 8: generation
# ---------------------------------------------------------------------------


def test_decision_brief_command_creates_brief_row(client) -> None:
    workspace = _create_workspace(client)
    session_id, _ordinals = _seed_session_with_citations(client, workspace["id"])

    response = client.post(
        "/chat/messages/stream",
        json={
            "workspace_id": workspace["id"],
            "session_id": session_id,
            "message": "/decision-brief",
        },
    )
    assert response.status_code == 200
    events = _parse_sse_events(response)

    brief_events = [e for e in events if e.get("type") == "decision_brief"]
    assert len(brief_events) == 1, events
    brief_id = brief_events[0]["brief_id"]
    message_id = brief_events[0]["message_id"]
    assert brief_id > 0
    assert message_id > 0
    assert brief_events[0]["approval_status"] == "draft"

    # Verify the assistant message is typed as decision_brief.
    detail = client.get(
        f"/chat/sessions/{session_id}?workspace_id={workspace['id']}",
    ).json()
    brief_messages = [m for m in detail["messages"] if m["message_type"] == "decision_brief"]
    assert len(brief_messages) == 1
    assert brief_messages[0]["decision_brief_id"] == brief_id

    # Verify the brief row.
    fetched = client.get(f"/decision-briefs/{brief_id}?workspace_id={workspace['id']}")
    assert fetched.status_code == 200
    brief = fetched.json()
    assert brief["approval_status"] == "draft"
    assert brief["sequence_number"] == 1
    assert "context_problem" in brief["content_json"]


def test_decision_brief_insufficient_context_returns_command_result(client) -> None:
    workspace = _create_workspace(client)
    # Lazy session, no assistant context, no citations.
    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "/decision-brief"},
    )
    events = _parse_sse_events(response)
    cmd_events = [e for e in events if e.get("type") == "command_result"]
    assert len(cmd_events) == 1
    assert cmd_events[0]["ok"] is False
    assert "Belum ada context" in cmd_events[0]["content"]

    # No decision brief row was created.
    from app.db.session import engine

    with Session(engine) as db:
        briefs = db.exec(select(DecisionBrief)).all()
        assert briefs == []


def test_decision_brief_sequence_numbers_increment(client) -> None:
    workspace = _create_workspace(client)
    session_id, _ = _seed_session_with_citations(client, workspace["id"])

    first = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "session_id": session_id, "message": "/decision-brief"},
    )
    second = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "session_id": session_id, "message": "/decision-brief"},
    )

    e1 = [e for e in _parse_sse_events(first) if e.get("type") == "decision_brief"][0]
    e2 = [e for e in _parse_sse_events(second) if e.get("type") == "decision_brief"][0]
    assert e1["sequence_number"] == 1
    assert e2["sequence_number"] == 2
    assert e1["brief_id"] != e2["brief_id"]


def test_decision_brief_validates_evidence_ordinals(client) -> None:
    """Citation refs in content_json must be ordinals present in the session."""
    workspace = _create_workspace(client)
    session_id, ordinals = _seed_session_with_citations(client, workspace["id"], citations=2)

    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "session_id": session_id, "message": "/decision-brief"},
    )
    event = [e for e in _parse_sse_events(response) if e.get("type") == "decision_brief"][0]
    brief = client.get(f"/decision-briefs/{event['brief_id']}?workspace_id={workspace['id']}").json()
    refs = brief["content_json"].get("source_evidence", [])
    # All refs must resolve to citations in the session.
    for ref in refs:
        assert ref["ordinal"] in ordinals


# ---------------------------------------------------------------------------
# Task 9: status transitions
# ---------------------------------------------------------------------------


def _create_brief(client, workspace_id: int) -> dict:
    session_id, _ = _seed_session_with_citations(client, workspace_id)
    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace_id, "session_id": session_id, "message": "/decision-brief"},
    )
    event = [e for e in _parse_sse_events(response) if e.get("type") == "decision_brief"][0]
    return client.get(f"/decision-briefs/{event['brief_id']}?workspace_id={workspace_id}").json()


def test_status_transition_draft_to_reviewed(client) -> None:
    workspace = _create_workspace(client)
    brief = _create_brief(client, workspace["id"])

    response = client.patch(
        f"/decision-briefs/{brief['id']}/status",
        json={"workspace_id": workspace["id"], "approval_status": "reviewed"},
    )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "reviewed"


def test_status_transition_approved_locks(client, monkeypatch) -> None:
    workspace = _create_workspace(client)
    brief = _create_brief(client, workspace["id"])

    # Mock the indexing side-effect so we don't need real ChromaDB.
    called = {}

    def fake_index_decision_brief(b):
        called["brief_id"] = b.id
        return 3

    monkeypatch.setattr(
        "app.knowledge.indexing.index_decision_brief", fake_index_decision_brief
    )

    response = client.patch(
        f"/decision-briefs/{brief['id']}/status",
        json={"workspace_id": workspace["id"], "approval_status": "approved"},
    )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    assert called.get("brief_id") == brief["id"]

    # Approved is locked: further transitions rejected with 422.
    locked = client.patch(
        f"/decision-briefs/{brief['id']}/status",
        json={"workspace_id": workspace["id"], "approval_status": "rejected"},
    )
    assert locked.status_code == 422


def test_status_transition_invalid_returns_422(client) -> None:
    workspace = _create_workspace(client)
    brief = _create_brief(client, workspace["id"])
    client.patch(
        f"/decision-briefs/{brief['id']}/status",
        json={"workspace_id": workspace["id"], "approval_status": "rejected"},
    )
    # Rejected is locked.
    response = client.patch(
        f"/decision-briefs/{brief['id']}/status",
        json={"workspace_id": workspace["id"], "approval_status": "approved"},
    )
    assert response.status_code == 422


def test_status_update_wrong_workspace_returns_404(client) -> None:
    workspace_a = _create_workspace(client, "A")
    workspace_b = _create_workspace(client, "B")
    brief = _create_brief(client, workspace_a["id"])

    response = client.patch(
        f"/decision-briefs/{brief['id']}/status",
        json={"workspace_id": workspace_b["id"], "approval_status": "reviewed"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Indexing on approval (Task 9 + cross-session reachability)
# ---------------------------------------------------------------------------


def test_list_decision_briefs_workspace_scoped(client) -> None:
    """GET /decision-briefs lists only the active workspace's briefs."""
    ws_a = _create_workspace(client, "WS A")
    ws_b = _create_workspace(client, "WS B")
    _create_brief(client, ws_a["id"])
    _create_brief(client, ws_b["id"])

    response = client.get(f"/decision-briefs?workspace_id={ws_a['id']}")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["workspace_id"] == ws_a["id"]


def test_list_decision_briefs_filters_by_approval_status(client) -> None:
    """approval_status query filters the result set."""
    workspace = _create_workspace(client)
    draft = _create_brief(client, workspace["id"])
    approved = _create_brief(client, workspace["id"])
    client.patch(
        f"/decision-briefs/{approved['id']}/status",
        json={"workspace_id": workspace["id"], "approval_status": "approved"},
    )

    all_rows = client.get(f"/decision-briefs?workspace_id={workspace['id']}").json()
    assert len(all_rows) == 2

    approved_rows = client.get(
        f"/decision-briefs?workspace_id={workspace['id']}&approval_status=approved"
    ).json()
    assert len(approved_rows) == 1
    assert approved_rows[0]["id"] == approved["id"]

    draft_rows = client.get(
        f"/decision-briefs?workspace_id={workspace['id']}&approval_status=draft"
    ).json()
    assert len(draft_rows) == 1
    assert draft_rows[0]["id"] == draft["id"]


def test_list_decision_briefs_empty_workspace_returns_empty(client) -> None:
    workspace = _create_workspace(client)
    response = client.get(f"/decision-briefs?workspace_id={workspace['id']}")
    assert response.status_code == 200
    assert response.json() == []


def test_index_decision_brief_upserts_sections(monkeypatch) -> None:
    """``index_decision_brief`` writes one Chroma doc per populated section."""
    upserts: list[dict] = []

    class FakeCollection:
        def upsert(self, ids, documents, metadatas):
            upserts.append({"ids": ids, "documents": documents, "metadatas": metadatas})

    monkeypatch.setattr(
        "app.knowledge.indexing.get_company_knowledge_collection",
        lambda: FakeCollection(),
    )

    from app.knowledge.indexing import index_decision_brief

    brief = DecisionBrief(
        id=42,
        workspace_id=7,
        chat_session_id=1,
        chat_message_id=2,
        sequence_number=1,
        title="Berlin expansion",
        objective="Decide whether to open a Berlin office in H2.",
        recommendation_status=DecisionRecommendationStatus.VALIDATE_FIRST,
        approval_status=DecisionApprovalStatus.APPROVED,
        content_json={
            "objective": "Open Berlin office in H2",
            "context_problem": "Demand growing in DE.",
            "strategic_interpretation": "Strong fit",
            "recommendation": "Validate hiring pipeline first",
            "risks_assumptions": ["Compliance unknown"],
            "next_steps": ["Run hiring market scan"],
        },
        created_at=datetime.utcnow(),
    )

    n = index_decision_brief(brief)
    assert n == 6
    assert len(upserts) == 1
    metas = upserts[0]["metadatas"]
    assert all(m["workspace_id"] == 7 for m in metas)
    assert all(m["decision_brief_id"] == 42 for m in metas)
    assert all(m["source_kind"] == "decision_brief" for m in metas)
    assert all(m["approval_status"] == "approved" for m in metas)
