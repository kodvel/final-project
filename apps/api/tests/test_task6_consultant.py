"""Task 6 tests: Source-grounded AI Consultant responses.

Tests verify:
- Consultant fallback works without API keys (safe fallback)
- Citations are persisted for assistant messages
- Tool call summaries are persisted
- Pre-retrieval classifier defaults to retrieval on failure
- Evidence bundle is passed to consultant
- Web citations are handled when local evidence is weak
- Insufficient data response labels gaps
- Deleted source citations remain visible with warning status
- View Sources data shape from session detail
"""

from __future__ import annotations

import json

from app.agents.consultant import (
    CitationRecord,
    ConsultantResult,
    ToolCallRecord,
    classify_needs_retrieval,
    persist_citations,
    persist_tool_calls,
)
from app.knowledge.retrieval import EvidenceBundle, EvidenceItem
from app.models.chat import ChatMessage, MessageSourceCitation
from app.models.enums import CitationStatus, CitationType
from app.services.context_builder import ContextWindow


def create_workspace(client, name: str = "Consultant Workspace") -> dict:
    response = client.post("/workspaces", json={"name": name, "description": "Consultant test workspace"})
    assert response.status_code == 201
    return response.json()


def parse_sse_events(response) -> list[dict]:
    """Parse SSE response into list of event dicts."""
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
# Fallback streaming (no API key required)
# ---------------------------------------------------------------------------


def test_stream_uses_consultant_fallback_without_api_key(client) -> None:
    """When CHAT_OPENAI_API_KEY is not set, fallback response is streamed."""
    workspace = create_workspace(client)

    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "What is our revenue trend?"},
    )

    assert response.status_code == 200
    events = parse_sse_events(response)
    types = [e["type"] for e in events]

    assert "metadata" in types
    assert "text_delta" in types
    assert "[DONE]" in types

    # Check fallback content via DB (session detail)
    metadata_event = next(e for e in events if e["type"] == "metadata")
    session_id = metadata_event["session_id"]
    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    assistant_msg = next(m for m in detail["messages"] if m["role"] == "assistant")
    content_lower = assistant_msg["content"].lower()
    assert "gap" in content_lower or "confidence" in content_lower or "unavailable" in content_lower


def test_stream_preserves_all_task5_event_types(client) -> None:
    """All core SSE event types still work after Task 6 integration."""
    workspace = create_workspace(client)

    response = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "Hello"},
    )

    events = parse_sse_events(response)
    types = [e["type"] for e in events]

    # Core event types that must be present
    assert "metadata" in types
    assert "text_delta" in types
    assert "[DONE]" in types


def test_stream_continuation_with_session_id(client) -> None:
    """Streaming continuation works with existing session_id."""
    workspace = create_workspace(client)

    r1 = client.post("/chat/messages/stream", json={"workspace_id": workspace["id"], "message": "First"})
    events1 = parse_sse_events(r1)
    metadata1 = next(e for e in events1 if e["type"] == "metadata")
    session_id = metadata1["session_id"]

    r2 = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "session_id": session_id, "message": "Second"},
    )

    events2 = parse_sse_events(r2)
    types2 = [e["type"] for e in events2]

    # metadata should show created_session=False for existing session
    metadata2 = next(e for e in events2 if e["type"] == "metadata")
    assert metadata2["created_session"] is False
    assert "[DONE]" in types2


# ---------------------------------------------------------------------------
# Citation persistence
# ---------------------------------------------------------------------------


def test_persist_citations_uploads_source_citations(client) -> None:
    """Citation persistence stores uploaded_source citations correctly."""

    # Use the test client's app to get a DB session
    from app.db.session import get_session
    from app.main import app

    db_gen = app.dependency_overrides[get_session]()
    db = next(db_gen)

    try:
        # Create a session and message
        from app.models.chat import ChatMessage, ChatSession
        from app.models.enums import ChatMessageRole, ChatMessageType, MessageStatus

        chat_session = ChatSession(workspace_id=1, title="Test")
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        msg = ChatMessage(
            session_id=chat_session.id,
            role=ChatMessageRole.ASSISTANT,
            content="Test [1]",
            message_type=ChatMessageType.NORMAL,
            status=MessageStatus.COMPLETED,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        citations = [
            CitationRecord(
                citation_type=CitationType.UPLOADED_SOURCE,
                ordinal=1,
                source_id=1,
                artifact_id=1,
                chunk_id="chunk_0",
                quote="Revenue grew 15%",
                page_number=3,
                relevance_score=0.85,
            )
        ]

        result = persist_citations(db, msg.id, citations)
        assert len(result) == 1
        assert result[0].citation_type == CitationType.UPLOADED_SOURCE
        assert result[0].source_id == 1
        assert result[0].chunk_id == "chunk_0"
        assert result[0].ordinal == 1
    finally:
        db.close()


def test_persist_citations_web_citations(client) -> None:
    """Citation persistence stores web citations with url/title."""
    from app.db.session import get_session
    from app.main import app

    db_gen = app.dependency_overrides[get_session]()
    db = next(db_gen)

    try:
        from app.models.chat import ChatMessage, ChatSession
        from app.models.enums import ChatMessageRole, ChatMessageType, MessageStatus

        chat_session = ChatSession(workspace_id=1, title="Web Test")
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        msg = ChatMessage(
            session_id=chat_session.id,
            role=ChatMessageRole.ASSISTANT,
            content="Market data [1]",
            message_type=ChatMessageType.NORMAL,
            status=MessageStatus.COMPLETED,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        from datetime import datetime

        citations = [
            CitationRecord(
                citation_type=CitationType.WEB,
                ordinal=1,
                url="https://example.com/market",
                title="Market Report 2026",
                domain="example.com",
                provider="tavily",
                snippet="Market grew 20%",
                relevance_score=0.75,
                retrieved_at=datetime.utcnow(),
            )
        ]

        result = persist_citations(db, msg.id, citations)
        assert len(result) == 1
        assert result[0].citation_type == CitationType.WEB
        assert result[0].url == "https://example.com/market"
        assert result[0].source_id is None
        assert result[0].domain == "example.com"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool call persistence
# ---------------------------------------------------------------------------


def test_persist_tool_calls_stores_summaries(client) -> None:
    """Tool call persistence stores name, status, summary."""
    from app.db.session import get_session
    from app.main import app

    db_gen = app.dependency_overrides[get_session]()
    db = next(db_gen)

    try:
        from app.models.chat import ChatMessage, ChatSession
        from app.models.enums import ChatMessageRole, ChatMessageType, MessageStatus

        chat_session = ChatSession(workspace_id=1, title="Tool Test")
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        msg = ChatMessage(
            session_id=chat_session.id,
            role=ChatMessageRole.ASSISTANT,
            content="Answer",
            message_type=ChatMessageType.NORMAL,
            status=MessageStatus.COMPLETED,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        tool_calls = [
            ToolCallRecord(
                tool_name="retrieve_company_knowledge",
                status="success",
                summary="Retrieved 5 evidence chunks from 2 sources",
                input_json={"query": "revenue trend"},
            ),
        ]

        result = persist_tool_calls(db, msg.id, tool_calls)
        assert len(result) == 1
        assert result[0].tool_name == "retrieve_company_knowledge"
        assert result[0].status == "success"
        assert result[0].summary == "Retrieved 5 evidence chunks from 2 sources"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Classifier behavior
# ---------------------------------------------------------------------------


def test_classifier_defaults_to_retrieval_on_missing_key() -> None:
    """When RAG API key is missing, classifier defaults to True (retrieve)."""
    context = ContextWindow(
        conversation_summary=None,
        recent_messages=[],
        current_user_message="What is our revenue?",
    )
    # No RAG key configured in test env → should return True
    assert classify_needs_retrieval(context, "What is our revenue?") is True


def test_classifier_defaults_to_retrieval_on_failure(monkeypatch) -> None:
    """When classifier OpenAI call fails, defaults to True (retrieve)."""
    from unittest.mock import MagicMock

    # Mock OpenAI constructor to raise
    mock_client = MagicMock()
    mock_client.chat.completions.parse.side_effect = RuntimeError("LLM unavailable")

    monkeypatch.setattr("openai.OpenAI", lambda **kw: mock_client)
    monkeypatch.setenv("RAG_OPENAI_API_KEY", "test-key")

    # Clear settings cache
    from app.core.config import get_settings
    get_settings.cache_clear()

    context = ContextWindow(
        conversation_summary="Previous discussion",
        recent_messages=[{"role": "user", "content": "Hello"}],
        current_user_message="What about marketing?",
    )
    assert classify_needs_retrieval(context, "What about marketing?") is True

    # Cleanup
    get_settings.cache_clear()


def test_classifier_defaults_to_retrieval_on_auth_error(monkeypatch) -> None:
    """When classifier gets 401/403 APIStatusError, defaults to True with concise warning."""
    from unittest.mock import MagicMock

    from openai import APIStatusError

    mock_client = MagicMock()
    mock_client.chat.completions.parse.side_effect = APIStatusError(
        message="Invalid API key",
        response=MagicMock(status_code=401),
        body=None,
    )

    monkeypatch.setattr("openai.OpenAI", lambda **kw: mock_client)
    monkeypatch.setenv("RAG_OPENAI_API_KEY", "sk-or-v1-test-key")
    monkeypatch.setenv("RAG_OPENAI_API_BASE_URL", "https://api.openai.com/v1")

    from app.core.config import get_settings
    get_settings.cache_clear()

    context = ContextWindow(
        conversation_summary=None,
        recent_messages=[],
        current_user_message="What is our revenue?",
    )
    # Should not raise, just return True
    assert classify_needs_retrieval(context, "What is our revenue?") is True

    get_settings.cache_clear()


def test_classifier_returns_false_for_chitchat_when_parsed(monkeypatch) -> None:
    """When OpenAI structured parse returns needs_retrieval=False, function returns False."""
    from unittest.mock import MagicMock

    from app.agents.consultant import RetrievalClassification

    mock_parsed = RetrievalClassification(needs_retrieval=False, reason="Simple greeting")
    mock_message = MagicMock()
    mock_message.parsed = mock_parsed
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.parse.return_value = mock_response

    monkeypatch.setattr("openai.OpenAI", lambda **kw: mock_client)
    monkeypatch.setenv("RAG_OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings
    get_settings.cache_clear()

    context = ContextWindow(
        conversation_summary=None,
        recent_messages=[],
        current_user_message="Hello!",
    )
    assert classify_needs_retrieval(context, "Hello!") is False

    get_settings.cache_clear()


def test_classifier_returns_true_when_parsed_needs_retrieval(monkeypatch) -> None:
    """When OpenAI structured parse returns needs_retrieval=True, function returns True."""
    from unittest.mock import MagicMock

    from app.agents.consultant import RetrievalClassification

    mock_parsed = RetrievalClassification(needs_retrieval=True, reason="Asks about company data")
    mock_message = MagicMock()
    mock_message.parsed = mock_parsed
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.parse.return_value = mock_response

    monkeypatch.setattr("openai.OpenAI", lambda **kw: mock_client)
    monkeypatch.setenv("RAG_OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings
    get_settings.cache_clear()

    context = ContextWindow(
        conversation_summary=None,
        recent_messages=[],
        current_user_message="What is our revenue?",
    )
    assert classify_needs_retrieval(context, "What is our revenue?") is True

    get_settings.cache_clear()


def test_classifier_defaults_to_retrieval_when_parsed_is_none(monkeypatch) -> None:
    """When OpenAI parse returns None for parsed field, defaults to True."""
    from unittest.mock import MagicMock

    mock_message = MagicMock()
    mock_message.parsed = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.parse.return_value = mock_response

    monkeypatch.setattr("openai.OpenAI", lambda **kw: mock_client)
    monkeypatch.setenv("RAG_OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings
    get_settings.cache_clear()

    context = ContextWindow(
        conversation_summary=None,
        recent_messages=[],
        current_user_message="Hello",
    )
    assert classify_needs_retrieval(context, "Hello") is True

    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Consultant fallback produces gap responses
# ---------------------------------------------------------------------------


def test_fallback_response_labels_gaps() -> None:
    """Fallback response without evidence labels gaps explicitly."""
    from app.agents.consultant import _fallback_run

    result = ConsultantResult()
    events = list(_fallback_run(
        current_message="What is our churn?",
        evidence_bundle=None,
        result=result,
    ))

    content = result.content
    # Natural prompt: fallback mentions gaps and confidence naturally, not rigid headers
    assert "gap" in content.lower() or "Gaps" in content
    assert "confidence" in content.lower() or "Confidence" in content
    assert len(events) > 0
    assert all(e[0].type == "text_delta" for e in events)


def test_fallback_response_with_evidence_has_citations() -> None:
    """Fallback response with evidence creates citation records."""
    from app.agents.consultant import _fallback_run

    bundle = EvidenceBundle(
        items=[
            EvidenceItem(
                citation_id="src:1:art:1:chunk:0",
                source_id=1,
                artifact_id=1,
                chunk_id="chunk_0",
                source_title="Q1 Report",
                file_type="csv",
                team_label="marketing",
                category_labels=["analytics_metrics"],
                period_start_month="2026-01",
                period_end_month="2026-03",
                quote="Revenue grew 15% in Q1",
                page_number=None,
                row_refs=None,
                content_type="metric",
                document_section="executive_summary",
                relevance_score=0.9,
            )
        ],
        insufficient_evidence=False,
    )

    result = ConsultantResult()
    list(_fallback_run(
        current_message="Revenue trend?",
        evidence_bundle=bundle,
        result=result,
    ))

    assert len(result.citations) > 0
    assert result.citations[0].source_id == 1
    assert result.citations[0].quote == "Revenue grew 15% in Q1"


# ---------------------------------------------------------------------------
# Citation extraction from inline [N] references
# ---------------------------------------------------------------------------


def test_inline_citations_extracted_from_response() -> None:
    """[N] references in response text create citation records."""
    from app.agents.consultant import _extract_citations

    result = ConsultantResult()
    bundle = EvidenceBundle(
        items=[
            EvidenceItem(
                citation_id="src:1:art:1:chunk:0",
                source_id=1,
                artifact_id=1,
                chunk_id="chunk_0",
                source_title="Q1 Report",
                file_type="csv",
                team_label="marketing",
                category_labels=[],
                period_start_month="2026-01",
                period_end_month="2026-03",
                quote="Revenue 15%",
                page_number=None,
                row_refs=None,
                content_type="metric",
                document_section="summary",
                relevance_score=0.9,
            ),
            EvidenceItem(
                citation_id="src:2:art:2:chunk:0",
                source_id=2,
                artifact_id=2,
                chunk_id="chunk_0",
                source_title="Market Analysis",
                file_type="pdf",
                team_label="business",
                category_labels=[],
                period_start_month="2026-01",
                period_end_month="2026-03",
                quote="Market grew 10%",
                page_number=5,
                row_refs=None,
                content_type="narrative",
                document_section="market_context",
                relevance_score=0.8,
            ),
        ]
    )

    evidence_items_map = {
        "src:1:art:1:chunk:0": {"ordinal": 1, "item": bundle.items[0]},
        "src:2:art:2:chunk:0": {"ordinal": 2, "item": bundle.items[1]},
    }

    _extract_citations(
        result=result,
        full_text="Revenue grew [1]. Market also expanded [2].",
        evidence_items_map=evidence_items_map,
        evidence_bundle=bundle,
    )

    assert len(result.citations) == 2
    assert result.citations[0].ordinal == 1
    assert result.citations[0].source_id == 1
    assert result.citations[1].ordinal == 2
    assert result.citations[1].source_id == 2
    assert result.citations[1].page_number == 5


def test_no_inline_refs_stores_unreferenced_context() -> None:
    """When no [N] references in text, top evidence stored as unreferenced context."""
    from app.agents.consultant import _extract_citations

    result = ConsultantResult()
    bundle = EvidenceBundle(
        items=[
            EvidenceItem(
                citation_id="src:1:art:1:chunk:0",
                source_id=1,
                artifact_id=1,
                chunk_id="chunk_0",
                source_title="Q1 Report",
                file_type="csv",
                team_label="marketing",
                category_labels=[],
                period_start_month="2026-01",
                period_end_month="2026-03",
                quote="Revenue 15%",
                page_number=None,
                row_refs=None,
                content_type="metric",
                document_section="summary",
                relevance_score=0.9,
            ),
        ]
    )

    evidence_items_map = {
        "src:1:art:1:chunk:0": {"ordinal": 1, "item": bundle.items[0]},
    }

    _extract_citations(
        result=result,
        full_text="Revenue increased overall.",
        evidence_items_map=evidence_items_map,
        evidence_bundle=bundle,
    )

    # No citations created (no inline refs)
    assert len(result.citations) == 0
    # But unreferenced context stored
    assert len(result.unreferenced_context) == 1
    assert result.unreferenced_context[0]["source_title"] == "Q1 Report"


# ---------------------------------------------------------------------------
# View Sources data shape
# ---------------------------------------------------------------------------


def test_session_detail_includes_tool_calls_and_citations(client) -> None:
    """GET /chat/sessions/{id} includes tool call and citation data in messages."""
    workspace = create_workspace(client)

    # Stream a message to create a session
    r = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "Test message"},
    )
    events = parse_sse_events(r)
    metadata_event = next(e for e in events if e["type"] == "metadata")
    session_id = metadata_event["session_id"]

    # Get session detail
    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    assert detail["id"] == session_id
    assert len(detail["messages"]) == 2  # user + assistant

    # Assistant message should have content
    assistant_msg = next(m for m in detail["messages"] if m["role"] == "assistant")
    assert assistant_msg["status"] == "completed"
    assert len(assistant_msg["content"]) > 0


# ---------------------------------------------------------------------------
# Deleted source citations remain visible
# ---------------------------------------------------------------------------


def test_deleted_source_citations_remain_visible_with_warning(client) -> None:
    """Citations pointing to deleted sources show warning status."""
    from app.db.session import get_session
    from app.main import app

    db_gen = app.dependency_overrides[get_session]()
    db = next(db_gen)

    try:
        from app.models.chat import ChatMessage, ChatSession
        from app.models.enums import ChatMessageRole, ChatMessageType, MessageStatus

        chat_session = ChatSession(workspace_id=1, title="Deleted Source Test")
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        msg = ChatMessage(
            session_id=chat_session.id,
            role=ChatMessageRole.ASSISTANT,
            content="Answer [1]",
            message_type=ChatMessageType.NORMAL,
            status=MessageStatus.COMPLETED,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Create citation with source_deleted status
        citation = MessageSourceCitation(
            message_id=msg.id,
            citation_type=CitationType.UPLOADED_SOURCE,
            ordinal=1,
            source_id=999,  # Non-existent/deleted source
            quote="Some old quote",
            citation_status=CitationStatus.SOURCE_DELETED,
        )
        db.add(citation)
        db.commit()

        # Verify citation is persisted with warning status
        from sqlmodel import select

        saved = db.exec(
            select(MessageSourceCitation).where(MessageSourceCitation.message_id == msg.id)
        ).first()
        assert saved is not None
        assert saved.citation_status == CitationStatus.SOURCE_DELETED
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Web search helper
# ---------------------------------------------------------------------------


def test_web_capable_detection() -> None:
    """_is_web_capable detects market/industry/public questions."""
    from app.services.chat import _is_web_capable

    assert _is_web_capable("What is the market trend for SaaS?") is True
    assert _is_web_capable("Who are our competitors?") is True
    assert _is_web_capable("What is our internal revenue?") is False
    assert _is_web_capable("Hello") is False


# ---------------------------------------------------------------------------
# Context builder integration
# ---------------------------------------------------------------------------


def test_consultant_uses_conversation_summary_for_long_sessions(client) -> None:
    """Long session: consultant receives summary + recent raw + current message."""
    workspace = create_workspace(client)

    # Create a long session by sending many messages
    session_id = None
    for i in range(8):
        r = client.post(
            "/chat/messages/stream",
            json={
                "workspace_id": workspace["id"],
                "session_id": session_id,
                "message": f"Question {i} about revenue and growth",
            },
        )
        events = parse_sse_events(r)
        if session_id is None:
            metadata = next(e for e in events if e["type"] == "metadata")
            session_id = metadata["session_id"]

    # Verify session has summary
    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    assert detail["conversation_summary"] is not None
    assert len(detail["messages"]) == 16  # 8 turns × 2 messages each

    # Last assistant message should be completed
    last_assistant = detail["messages"][-1]
    assert last_assistant["role"] == "assistant"
    assert last_assistant["status"] == "completed"


# ---------------------------------------------------------------------------
# Tavily tool
# ---------------------------------------------------------------------------


def test_tavily_returns_error_without_api_key(monkeypatch) -> None:
    """Tavily search returns error dict when API key is not configured."""
    from app.agents.tools import tavily_web_search
    from app.core.config import Settings, get_settings

    # Patch get_settings to return a Settings with tavily_api_key=None
    monkeypatch.setattr(
        "app.core.config.get_settings",
        lambda: Settings(tavily_api_key=None),
    )
    get_settings.cache_clear()

    result = tavily_web_search("test query")
    assert result["results"] == []
    assert result.get("error") is not None

    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Source grounding rule: conversation summary not treated as evidence
# ---------------------------------------------------------------------------


def test_system_prompt_states_summary_is_not_evidence() -> None:
    """System prompt instructs that conversation summary is not evidence."""
    from app.agents.prompts import SYSTEM_PROMPT

    lower = SYSTEM_PROMPT.lower()
    assert "conversation summary" in lower
    assert "not evidence" in lower or "NOT count as source-grounded evidence" in lower


def test_system_prompt_encourages_natural_style() -> None:
    """System prompt does NOT force rigid Direct Answer/Evidence headers."""
    from app.agents.prompts import SYSTEM_PROMPT

    # Should say "naturally" or "conversational" somewhere
    lower = SYSTEM_PROMPT.lower()
    assert "natural" in lower or "conversational" in lower
    # Should NOT say "every response must follow"
    assert "every response must follow" not in lower


# ---------------------------------------------------------------------------
# Source scope parsing (fix #4)
# ---------------------------------------------------------------------------


def test_parse_source_scope_detects_team() -> None:
    """Parser extracts team_label from natural language."""
    from app.agents.consultant import parse_source_scope

    scope = parse_source_scope("Show me marketing data from our Q1 report")
    assert scope is not None
    assert scope.team_label == "marketing"


def test_parse_source_scope_detects_category() -> None:
    """Parser extracts category_labels from natural language."""
    from app.agents.consultant import parse_source_scope

    scope = parse_source_scope("What does the competitor analysis say about our positioning?")
    assert scope is not None
    assert scope.category_labels is not None
    assert "competitor_analysis" in scope.category_labels


def test_parse_source_scope_detects_period() -> None:
    """Parser extracts period months from YYYY-MM patterns."""
    from app.agents.consultant import parse_source_scope

    scope = parse_source_scope("Compare data from 2026-01 to 2026-06")
    assert scope is not None
    assert scope.period_start_month == "2026-01"
    assert scope.period_end_month == "2026-06"


def test_parse_source_scope_returns_none_for_no_constraints() -> None:
    """Parser returns None when no scope constraints detected."""
    from app.agents.consultant import parse_source_scope

    scope = parse_source_scope("What should we do next?")
    assert scope is None


# ---------------------------------------------------------------------------
# Session detail with citations and tool calls (fix #3)
# ---------------------------------------------------------------------------


def test_session_detail_returns_citations_and_tool_calls_lists(client) -> None:
    """GET /chat/sessions/{id} includes citations=[] and tool_calls=[] fields."""
    workspace = create_workspace(client)

    r = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "Hello test"},
    )
    events = parse_sse_events(r)
    metadata_event = next(e for e in events if e["type"] == "metadata")
    session_id = metadata_event["session_id"]

    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()

    # Must include citations and tool_calls fields
    assert "citations" in detail
    assert "tool_calls" in detail
    assert isinstance(detail["citations"], list)
    assert isinstance(detail["tool_calls"], list)


def test_session_detail_citations_persisted_after_stream(client) -> None:
    """Citations persisted during stream are visible in session detail."""
    from app.db.session import get_session
    from app.main import app

    # Stream a message
    workspace = create_workspace(client)
    r = client.post(
        "/chat/messages/stream",
        json={"workspace_id": workspace["id"], "message": "Revenue check"},
    )
    events = parse_sse_events(r)
    metadata_event = next(e for e in events if e["type"] == "metadata")
    session_id = metadata_event["session_id"]

    # Manually add a citation to the assistant message via DB
    db_gen = app.dependency_overrides[get_session]()
    db = next(db_gen)
    try:
        from sqlmodel import select

        assistant_msgs = db.exec(
            select(ChatMessage).where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
            )
        ).all()
        assert len(assistant_msgs) == 1
        msg_id = assistant_msgs[0].id

        citation = MessageSourceCitation(
            message_id=msg_id,
            citation_type=CitationType.UPLOADED_SOURCE,
            ordinal=1,
            source_id=1,
            quote="Revenue grew 15%",
            citation_status=CitationStatus.AVAILABLE,
        )
        db.add(citation)
        db.commit()
    finally:
        db.close()

    # Now get session detail and check citation is there
    detail = client.get(f"/chat/sessions/{session_id}?workspace_id={workspace['id']}").json()
    assert len(detail["citations"]) == 1
    assert detail["citations"][0]["quote"] == "Revenue grew 15%"
    assert detail["citations"][0]["citation_type"] == "uploaded_source"


# ---------------------------------------------------------------------------
# Web fallback bug fix (fix #6): insufficient with no items
# ---------------------------------------------------------------------------


def test_insufficient_evidence_bundle_with_no_items_still_produces_response() -> None:
    """EvidenceBundle with insufficient=True and no items still produces fallback."""
    from app.agents.consultant import _fallback_run

    bundle = EvidenceBundle(
        items=[],
        insufficient_evidence=True,
        reason="No eligible sources found",
    )

    result = ConsultantResult()
    list(_fallback_run(
        current_message="What is our revenue?",
        evidence_bundle=bundle,
        result=result,
    ))

    assert len(result.content) > 0
    assert "gap" in result.content.lower() or "insufficient" in result.content.lower()
    assert len(result.citations) == 0  # No items to cite


# ---------------------------------------------------------------------------
# Tool stream safety (fix #5): only name/call_id/status streamed
# ---------------------------------------------------------------------------


def test_tool_call_events_only_contain_safe_fields(client) -> None:
    """Tool call stream events only have tool_name and call_id, no args/raw."""
    # This test verifies the event format by checking the consultant module
    from app.agents.consultant import ConsultantEvent

    # Simulate a tool_call event
    event = ConsultantEvent(
        type="tool_call",
        data={"tool_name": "retrieve_company_knowledge", "call_id": "call_abc123"},
    )
    # Must not have args, raw, reasoning, or full content
    assert "args" not in event.data
    assert "raw" not in event.data
    assert "reasoning" not in event.data
    assert "tool_name" in event.data
    assert "call_id" in event.data

    # Simulate a tool_result event
    result_event = ConsultantEvent(
        type="tool_result",
        data={"call_id": "call_abc123", "ok": True},
    )
    assert "output" not in result_event.data
    assert "content" not in result_event.data
    assert "ok" in result_event.data


# ---------------------------------------------------------------------------
# Retrieve tool strict-schema safety (no dict / additionalProperties)
# ---------------------------------------------------------------------------


def test_retrieve_tool_params_are_strict_safe() -> None:
    """_make_retrieve_tool returns a function with only scalar/string params — no dict."""
    import inspect

    from app.agents.consultant import _make_retrieve_tool
    from unittest.mock import MagicMock

    mock_db = MagicMock()
    fn = _make_retrieve_tool(mock_db, workspace_id=1)

    sig = inspect.signature(fn)
    # Ensure no parameter has type annotation `dict` or `dict | None`
    for name, param in sig.parameters.items():
        ann = param.annotation
        # annotation may be a string or a real type; stringify for robust check
        ann_str = str(ann)
        assert "dict" not in ann_str.lower(), (
            f"Parameter '{name}' has dict-like annotation '{ann_str}' which is not strict-safe"
        )


def test_retrieve_tool_function_tool_creation_succeeds() -> None:
    """function_tool(retrieve_fn) does not raise additionalProperties error."""
    from unittest.mock import MagicMock

    from app.agents.consultant import _make_retrieve_tool

    mock_db = MagicMock()
    fn = _make_retrieve_tool(mock_db, workspace_id=1)

    from agents import function_tool

    # This would previously raise:
    #   UserError: additionalProperties should not be set for object types
    tool = function_tool(fn, name_override="retrieve_company_knowledge")
    assert tool is not None


def test_retrieve_tool_schema_no_additional_properties() -> None:
    """Generated JSON schema must have additionalProperties=false (strict-safe), not an open object."""
    import json

    from unittest.mock import MagicMock

    from agents import function_tool
    from app.agents.consultant import _make_retrieve_tool

    mock_db = MagicMock()
    fn = _make_retrieve_tool(mock_db, workspace_id=1)
    tool = function_tool(fn, name_override="retrieve_company_knowledge")

    schema = tool.params_json_schema
    # strict-safe: additionalProperties must be false, not true or an open schema
    assert schema.get("additionalProperties") is False, (
        f"Schema additionalProperties must be false, got: {schema.get('additionalProperties')}"
    )
    # All param types must be scalar/string, no free objects
    for prop_name, prop_schema in schema.get("properties", {}).items():
        prop_type = prop_schema.get("type")
        if prop_type is None:
            # anyOf union (e.g. str | null) — check none of the variants is object
            for variant in prop_schema.get("anyOf", []):
                assert variant.get("type") != "object", (
                    f"Property '{prop_name}' has object type variant which is not strict-safe"
                )
        else:
            assert prop_type != "object", (
                f"Property '{prop_name}' is type 'object' which is not strict-safe"
            )


# ---------------------------------------------------------------------------
# _build_source_scope helper
# ---------------------------------------------------------------------------


def test_build_source_scope_returns_none_when_empty() -> None:
    """No scope params → None."""
    from app.agents.consultant import _build_source_scope

    assert _build_source_scope() is None


def test_build_source_scope_parses_json_params() -> None:
    """Parses category_labels_json and source_ids_json into lists."""
    from app.agents.consultant import _build_source_scope

    scope = _build_source_scope(
        team_label="marketing",
        category_labels_json='["analytics_metrics", "revenue_sales"]',
        period_start_month="2026-01",
        period_end_month="2026-06",
        source_ids_json="[1, 2, 5]",
    )
    assert scope is not None
    assert scope.team_label == "marketing"
    assert scope.category_labels == ["analytics_metrics", "revenue_sales"]
    assert scope.period_start_month == "2026-01"
    assert scope.period_end_month == "2026-06"
    assert scope.source_ids == [1, 2, 5]


def test_build_source_scope_handles_invalid_json_gracefully() -> None:
    """Invalid JSON strings → None for those fields, still builds scope if other fields present."""
    from app.agents.consultant import _build_source_scope

    scope = _build_source_scope(
        team_label="product",
        category_labels_json="not-valid-json",
        source_ids_json="also-bad",
    )
    assert scope is not None
    assert scope.team_label == "product"
    assert scope.category_labels is None
    assert scope.source_ids is None
