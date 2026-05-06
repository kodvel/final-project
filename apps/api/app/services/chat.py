"""Chat session and message orchestration."""

from datetime import datetime

from sqlalchemy import asc, desc
from sqlmodel import Session, select

from app.models.chat import ChatMessage, ChatSession
from app.models.enums import ChatMessageRole, ChatMessageType
from app.models.workspace import Workspace

DEFAULT_SESSION_TITLE = "New Chat"


def create_session(session: Session, workspace_id: int, title: str | None = None) -> ChatSession:
    """Create a Chat Session permanently scoped to one Workspace."""
    if session.get(Workspace, workspace_id) is None:
        raise ValueError(f"Workspace {workspace_id} not found")

    chat_session = ChatSession(workspace_id=workspace_id, title=_clean_title(title) or DEFAULT_SESSION_TITLE)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def list_sessions(session: Session, workspace_id: int) -> list[ChatSession]:
    """List Chat Sessions for one Workspace, newest first."""
    return list(
        session.exec(
            select(ChatSession)
            .where(ChatSession.workspace_id == workspace_id)
            .order_by(desc(ChatSession.updated_at), desc(ChatSession.id))
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


def send_message(session: Session, session_id: int, workspace_id: int, content: str) -> tuple[ChatMessage, ChatMessage]:
    """Persist a user message and a dummy assistant response for Task 5."""
    chat_session = get_session_for_workspace(session, session_id, workspace_id)
    if chat_session is None:
        raise ValueError(f"Chat Session {session_id} not found for Workspace {workspace_id}")

    clean_content = content.strip()
    if not clean_content:
        raise ValueError("Message content is required")

    user_message = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.USER,
        content=clean_content,
        message_type=ChatMessageType.NORMAL,
    )
    session.add(user_message)
    session.flush()

    if chat_session.title == DEFAULT_SESSION_TITLE:
        chat_session.title = _title_from_message(clean_content)

    assistant_message = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.ASSISTANT,
        content=_dummy_assistant_response(clean_content),
        message_type=ChatMessageType.NORMAL,
    )
    session.add(assistant_message)
    chat_session.updated_at = datetime.utcnow()
    session.add(chat_session)

    session.commit()
    session.refresh(user_message)
    session.refresh(assistant_message)
    return user_message, assistant_message


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
