"""Chat session and message orchestration."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Generator

from sqlalchemy import asc, desc
from sqlmodel import Session, select

from app.models.chat import ChatMessage, ChatSession
from app.models.enums import ChatMessageRole, ChatMessageType, MessageStatus
from app.models.workspace import Workspace
from app.services.context_builder import ContextWindow, build_context

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TITLE = "New Chat"

# Dummy streaming response split into chunks for SSE simulation.
_DUMMY_CHUNKS = [
    "Direct Answer: ",
    "I saved your message to this Workspace-scoped Chat Session. ",
    "This is a placeholder streaming assistant response until the source-grounded AI Consultant is implemented.\n\n",
    "Next Step: ",
    "Upload or process Sources, then Task 6 can replace this dummy response with grounded evidence, "
    "citations, interpretation, recommendation, confidence, and gaps.",
]


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
    context = build_context_for_session(session, chat_session, clean_content)

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
    - streaming text delta chunks
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
    session_created = False

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
        session_created = True
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

    # Stream dummy text deltas
    collected_content: list[str] = []
    try:
        for chunk in _DUMMY_CHUNKS:
            collected_content.append(chunk)
            yield _sse_event({"type": "text_delta", "delta": chunk})
            time.sleep(0)  # yield control; real LLM would be async

        # Finalise assistant message
        full_content = "".join(collected_content)
        completed_at = datetime.utcnow()
        assistant_msg.content = full_content
        assistant_msg.status = MessageStatus.COMPLETED
        assistant_msg.completed_at = completed_at
        assistant_msg.updated_at = completed_at
        db.add(assistant_msg)

        chat_session.last_message_at = completed_at
        chat_session.updated_at = completed_at
        db.add(chat_session)
        db.commit()
        db.refresh(assistant_msg)

        yield _sse_event({
            "type": "assistant_completed",
            "message": _message_dict(assistant_msg),
        })
    except Exception:
        logger.exception("Error during streaming, marking assistant message as interrupted")
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
