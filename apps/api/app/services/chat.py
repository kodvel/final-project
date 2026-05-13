"""Chat session and message orchestration."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Generator

from sqlalchemy import asc, desc
from sqlmodel import Session, select

from app.agents.consultant import (
    ConsultantResult,
    classify_needs_retrieval,
    parse_source_scope,
    persist_citations,
    persist_tool_calls,
    run_consultant_stream,
)
from app.agents.tools import tavily_web_search
from app.knowledge.retrieval import (
    EvidenceBundle,
    retrieve_company_knowledge,
)
from app.models.chat import AgentToolCall, ChatMessage, ChatSession, MessageSourceCitation
from app.models.enums import ChatMessageRole, ChatMessageType, MessageStatus
from app.models.workspace import Workspace
from app.services.context_builder import ContextWindow, build_context

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TITLE = "New Chat"


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

def create_session(session: Session, workspace_id: int, title: str | None = None) -> ChatSession:
    """Create a Chat Session permanently scoped to one Workspace."""
    if session.get(Workspace, workspace_id) is None:
        raise ValueError(f"Workspace {workspace_id} not found")

    chat_session = ChatSession(workspace_id=workspace_id, title=_clean_title(title) or DEFAULT_SESSION_TITLE)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def list_sessions(session: Session, workspace_id: int, limit: int = 5, offset: int = 0) -> list[ChatSession]:
    """List Chat Sessions for one Workspace, newest first, with pagination."""
    return list(
        session.exec(
            select(ChatSession)
            .where(ChatSession.workspace_id == workspace_id)
            .order_by(desc(ChatSession.updated_at), desc(ChatSession.id))
            .limit(limit)
            .offset(offset)
        ).all()
    )


def get_session(session: Session, session_id: int) -> ChatSession | None:
    """Get a Chat Session by id."""
    return session.get(ChatSession, session_id)


def get_session_for_workspace(session: Session, session_id: int, workspace_id: int) -> ChatSession | None:
    """Get a Chat Session only when it belongs to the explicit Workspace scope."""
    return session.exec(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.workspace_id == workspace_id,
        )
    ).first()


def list_messages(session: Session, session_id: int) -> list[ChatMessage]:
    """List messages in chronological order for one Chat Session."""
    return list(
        session.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(asc(ChatMessage.created_at), asc(ChatMessage.id))
        ).all()
    )


def list_citations_for_session(session: Session, session_id: int) -> list[MessageSourceCitation]:
    """List all citations for all messages in a session (for View Sources)."""
    # Get all message IDs for the session
    msg_ids = session.exec(
        select(ChatMessage.id).where(ChatMessage.session_id == session_id)
    ).all()
    if not msg_ids:
        return []
    return list(
        session.exec(
            select(MessageSourceCitation)
            .where(MessageSourceCitation.message_id.in_(msg_ids))
            .order_by(asc(MessageSourceCitation.message_id), asc(MessageSourceCitation.ordinal))
        ).all()
    )


def list_tool_calls_for_session(session: Session, session_id: int) -> list[AgentToolCall]:
    """List all tool calls for all messages in a session."""
    msg_ids = session.exec(
        select(ChatMessage.id).where(ChatMessage.session_id == session_id)
    ).all()
    if not msg_ids:
        return []
    return list(
        session.exec(
            select(AgentToolCall)
            .where(AgentToolCall.message_id.in_(msg_ids))
            .order_by(asc(AgentToolCall.message_id), asc(AgentToolCall.id))
        ).all()
    )


# ---------------------------------------------------------------------------
# Legacy non-streaming send (kept for backward compat)
# ---------------------------------------------------------------------------

def send_message(session: Session, session_id: int, workspace_id: int, content: str) -> tuple[ChatMessage, ChatMessage]:
    """Persist a user message and a dummy assistant response for Task 5."""
    chat_session = get_session_for_workspace(session, session_id, workspace_id)
    if chat_session is None:
        raise ValueError(f"Chat Session {session_id} not found for Workspace {workspace_id}")

    clean_content = content.strip()
    if not clean_content:
        raise ValueError("Message content is required")

    now = datetime.utcnow()
    user_message = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.USER,
        content=clean_content,
        message_type=ChatMessageType.NORMAL,
        status=MessageStatus.COMPLETED,
        completed_at=now,
        updated_at=now,
    )
    session.add(user_message)
    session.flush()

    if chat_session.title == DEFAULT_SESSION_TITLE:
        chat_session.title = _title_from_message(clean_content)

    # Build context window (triggers summary refresh for long sessions)
    build_context_for_session(session, chat_session, clean_content)

    assistant_message = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.ASSISTANT,
        content=_dummy_assistant_response(clean_content),
        message_type=ChatMessageType.NORMAL,
        status=MessageStatus.COMPLETED,
        completed_at=now,
        updated_at=now,
    )
    session.add(assistant_message)
    chat_session.updated_at = now
    chat_session.last_message_at = now
    session.add(chat_session)

    session.commit()
    session.refresh(user_message)
    session.refresh(assistant_message)
    return user_message, assistant_message


# ---------------------------------------------------------------------------
# SSE streaming orchestration
# ---------------------------------------------------------------------------

def _sse_event(data: dict | str) -> str:
    """Format a single SSE data line.

    ``data`` is either a dict (serialised to JSON) or the literal string
    ``[DONE]`` which signals stream end.
    """
    payload = json.dumps(data) if isinstance(data, dict) else data
    return f"data: {payload}\n\n"


def stream_chat(db: Session, workspace_id: int, session_id: int | None, message: str) -> Generator[str, None, None]:
    """Yield SSE-formatted events for a chat interaction.

    This generator handles:
    - workspace validation
    - lazy session creation
    - user message persistence (completed)
    - assistant message creation (streaming → completed)
    - pre-retrieval classification and evidence retrieval
    - consultant agent streaming with tool calls and citations
    - error / interrupted status on exceptions

    The caller should wrap in a ``StreamingResponse`` with
    ``media_type="text/event-stream"``.
    """
    clean_message = message.strip()
    if not clean_message:
        yield _sse_event({"type": "error", "error": "Message content is required"})
        return

    # Validate workspace
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        yield _sse_event({"type": "error", "error": f"Workspace {workspace_id} not found"})
        return

    now = datetime.utcnow()

    # Lazy session creation
    if session_id is None:
        chat_session = ChatSession(
            workspace_id=workspace_id,
            title=DEFAULT_SESSION_TITLE,
            last_message_at=now,
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        session_id = chat_session.id
        yield _sse_event({
            "type": "session_created",
            "session": _session_dict(db, session_id),  # type: ignore[arg-type]
        })
    else:
        chat_session = get_session_for_workspace(db, session_id, workspace_id)
        if chat_session is None:
            yield _sse_event({"type": "error", "error": f"Chat Session {session_id} not found for Workspace {workspace_id}"})
            return

    # Save user message as completed
    user_msg = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.USER,
        content=clean_message,
        message_type=ChatMessageType.NORMAL,
        status=MessageStatus.COMPLETED,
        completed_at=now,
        updated_at=now,
    )
    db.add(user_msg)

    # Update session title from first message
    if chat_session.title == DEFAULT_SESSION_TITLE:
        chat_session.title = _title_from_message(clean_message)
    chat_session.last_message_at = now
    chat_session.updated_at = now
    db.add(chat_session)
    db.commit()
    db.refresh(user_msg)

    yield _sse_event({
        "type": "user_message_saved",
        "message": _message_dict(user_msg),
    })

    # Build context window (triggers summary refresh for long sessions)
    context = build_context_for_session(db, chat_session, clean_message)
    logger.debug(
        "Context built for session %s: total=%d, recent=%d, summary=%s",
        session_id,
        context.total_message_count,
        len(context.recent_messages),
        "yes" if context.conversation_summary else "no",
    )

    # Create assistant message as streaming
    assistant_msg = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.ASSISTANT,
        content="",
        message_type=ChatMessageType.NORMAL,
        status=MessageStatus.STREAMING,
        updated_at=datetime.utcnow(),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    yield _sse_event({
        "type": "assistant_started",
        "message": _message_dict(assistant_msg),
    })

    # --- Task 6: Pre-retrieval classification and evidence ---
    evidence_bundle: EvidenceBundle | None = None
    web_results: list[dict] = []
    needs_retrieval = classify_needs_retrieval(context, clean_message)

    if needs_retrieval:
        try:
            # Parse natural-language source scope from user message
            source_scope = parse_source_scope(clean_message)
            evidence_bundle = retrieve_company_knowledge(
                db,
                workspace_id,
                clean_message,
                source_scope=source_scope,
            )
        except Exception:
            logger.warning("Pre-retrieval failed", exc_info=True)
            evidence_bundle = EvidenceBundle(insufficient_evidence=True, reason="Retrieval error")

        # Stream sources_used if evidence found
        if evidence_bundle and evidence_bundle.items:
            citations_data = []
            for item in evidence_bundle.items:
                citations_data.append({
                    "source_title": item.source_title,
                    "file_type": item.file_type,
                    "quote": item.quote[:200] if item.quote else None,
                    "page_number": item.page_number,
                    "relevance_score": item.relevance_score,
                })
            yield _sse_event({
                "type": "sources_used",
                "citations": citations_data,
            })

            # Check if Tavily fallback is needed (weak evidence + web-capable question)
            if evidence_bundle.insufficient_evidence and _is_web_capable(clean_message):
                web_results = _try_tavily_search(clean_message)
                if web_results:
                    yield _sse_event({
                        "type": "web_sources_used",
                        "citations": web_results,
                    })

    # --- Run consultant agent ---
    collected_content: list[str] = []
    final_result: ConsultantResult | None = None

    try:
        for event, result in run_consultant_stream(
            db=db,
            workspace_id=workspace_id,
            context=context,
            evidence_bundle=evidence_bundle,
        ):
            final_result = result
            yield _sse_event({"type": event.type, **event.data})

        if final_result:
            collected_content.append(final_result.content)
    except Exception:
        logger.exception("Error during consultant streaming, marking assistant message as interrupted")
        partial = "".join(collected_content)
        interrupted_at = datetime.utcnow()
        assistant_msg.content = partial
        assistant_msg.status = MessageStatus.INTERRUPTED
        assistant_msg.error_message = "Stream interrupted"
        assistant_msg.updated_at = interrupted_at
        db.add(assistant_msg)
        db.commit()
        yield _sse_event({"type": "error", "error": "Stream interrupted"})
        return

    # Finalise assistant message
    full_content = "".join(collected_content)
    completed_at = datetime.utcnow()
    assistant_msg.content = full_content
    assistant_msg.status = MessageStatus.COMPLETED
    assistant_msg.completed_at = completed_at
    assistant_msg.updated_at = completed_at

    # Store unreferenced context in metadata if present
    if final_result and final_result.unreferenced_context:
        assistant_msg.metadata_json = {
            "unreferenced_context": final_result.unreferenced_context,
        }

    db.add(assistant_msg)

    # Persist tool calls
    if final_result and final_result.tool_calls:
        persist_tool_calls(db, assistant_msg.id, final_result.tool_calls)

    # Persist citations
    if final_result and final_result.citations:
        persist_citations(db, assistant_msg.id, final_result.citations)

    # Persist web citations
    if web_results and final_result:
        from app.agents.consultant import persist_web_citations

        start_ordinal = (len(final_result.citations) + 1) if final_result.citations else 1
        persist_web_citations(db, assistant_msg.id, web_results, start_ordinal=start_ordinal)

    chat_session.last_message_at = completed_at
    chat_session.updated_at = completed_at
    db.add(chat_session)
    db.commit()
    db.refresh(assistant_msg)

    yield _sse_event({
        "type": "assistant_completed",
        "message": _message_dict(assistant_msg),
    })

    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Context builder (delegates to context_builder service)
# ---------------------------------------------------------------------------

def build_context_for_session(
    db: Session,
    chat_session: ChatSession,
    current_user_message: str | None = None,
) -> "ContextWindow":
    """Build a budgeted context window for the session.

    Thin wrapper around the real context_builder service.
    """
    return build_context(
        db=db,
        chat_session=chat_session,
        current_user_message=current_user_message,
    )


# ---------------------------------------------------------------------------
# Tavily helper
# ---------------------------------------------------------------------------


def _is_web_capable(message: str) -> bool:
    """Heuristic check: is the question likely web-answerable?

    Simple check: if the message contains market, industry, competitor,
    public, or general knowledge keywords, consider it web-capable.
    """
    web_keywords = [
        "market", "industry", "competitor", "trend", "benchmark",
        "public", "general", "average", "standard", "best practice",
        "research", "news", "latest", "current",
    ]
    lower = message.lower()
    return any(kw in lower for kw in web_keywords)


def _try_tavily_search(query: str) -> list[dict]:
    """Try Tavily web search, return simplified results or empty list."""
    try:
        result = tavily_web_search(query)
        return result.get("results", [])
    except Exception:
        logger.warning("Tavily search failed", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_dict(db: Session, session_id: int) -> dict:
    chat_session = db.get(ChatSession, session_id)
    return {
        "id": chat_session.id,
        "workspace_id": chat_session.workspace_id,
        "title": chat_session.title,
        "created_at": chat_session.created_at.isoformat(),
        "updated_at": chat_session.updated_at.isoformat(),
        "last_message_at": chat_session.last_message_at.isoformat() if chat_session.last_message_at else None,
        "conversation_summary": chat_session.conversation_summary,
        "summary_cutoff_message_id": chat_session.summary_cutoff_message_id,
        "summary_updated_at": chat_session.summary_updated_at.isoformat() if chat_session.summary_updated_at else None,
    }


def _message_dict(msg: ChatMessage) -> dict:
    return {
        "id": msg.id,
        "session_id": msg.session_id,
        "role": msg.role,
        "content": msg.content,
        "message_type": msg.message_type,
        "status": msg.status,
        "error_message": msg.error_message,
        "trace_id": msg.trace_id,
        "created_at": msg.created_at.isoformat(),
        "updated_at": msg.updated_at.isoformat(),
        "completed_at": msg.completed_at.isoformat() if msg.completed_at else None,
    }


def _clean_title(title: str | None) -> str | None:
    if title is None:
        return None
    cleaned = title.strip()
    return cleaned[:80] if cleaned else None


def _title_from_message(content: str) -> str:
    title = " ".join(content.split())
    return title[:77] + "..." if len(title) > 80 else title


def _dummy_assistant_response(content: str) -> str:
    return (
        "Direct Answer: I saved your message to this Workspace-scoped Chat Session. "
        "Task 5 uses a placeholder assistant response until the source-grounded AI Consultant is implemented.\n\n"
        f"Your question: {content}\n\n"
        "Next Step: Upload or process Sources, then Task 6 can replace this dummy response with grounded evidence, citations, "
        "interpretation, recommendation, confidence, and gaps."
    )
