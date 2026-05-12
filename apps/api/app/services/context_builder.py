"""Context builder for chat session continuity.

Builds a budgeted context window for each turn:
- Short sessions: all messages returned raw, no summary needed.
- Long sessions: older messages collapsed into a deterministic conversation_summary
  (role-prefixed excerpts, no LLM), recent N messages kept raw.

Summary is context, not evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlmodel import Session, select

from app.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

DEFAULT_RECENT_WINDOW = 10
DEFAULT_MAX_SUMMARY_CHARS = 2000


@dataclass
class ContextWindow:
    """Structured context returned by the context builder."""

    conversation_summary: str | None = None
    summary_cutoff_message_id: int | None = None
    recent_messages: list[dict] = field(default_factory=list)
    current_user_message: str | None = None
    total_message_count: int = 0


def build_context(
    db: Session,
    chat_session: ChatSession,
    current_user_message: str | None = None,
    recent_messages_raw: int = DEFAULT_RECENT_WINDOW,
    max_summary_chars: int = DEFAULT_MAX_SUMMARY_CHARS,
) -> ContextWindow:
    """Build a budgeted context window for the session.

    For short sessions (<= recent_messages_raw), all messages are returned raw
    and no summary is generated.

    For long sessions, older messages beyond the recent window are collapsed
    into a deterministic summary stored on the ChatSession model. The summary
    uses role-prefixed excerpts — no LLM required.

    Args:
        db: SQLModel database session.
        chat_session: The ChatSession ORM object (will be mutated if summary refreshed).
        current_user_message: The user message being sent this turn (optional).
        recent_messages_raw: How many recent messages to keep raw.
        max_summary_chars: Maximum character budget for the summary.

    Returns:
        ContextWindow with summary, recent messages, and optional current message.
    """
    messages = _get_ordered_messages(db, chat_session.id)
    total = len(messages)

    # --- Short session: everything raw, no summary ---
    if total <= recent_messages_raw:
        return ContextWindow(
            conversation_summary=chat_session.conversation_summary,
            summary_cutoff_message_id=chat_session.summary_cutoff_message_id,
            recent_messages=[_message_to_dict(m) for m in messages],
            current_user_message=current_user_message,
            total_message_count=total,
        )

    # --- Long session: refresh summary, keep recent raw ---
    _maybe_refresh_summary(
        db=db,
        chat_session=chat_session,
        messages=messages,
        recent_window=recent_messages_raw,
        max_summary_chars=max_summary_chars,
    )

    recent = messages[-recent_messages_raw:]
    return ContextWindow(
        conversation_summary=chat_session.conversation_summary,
        summary_cutoff_message_id=chat_session.summary_cutoff_message_id,
        recent_messages=[_message_to_dict(m) for m in recent],
        current_user_message=current_user_message,
        total_message_count=total,
    )


def _maybe_refresh_summary(
    db: Session,
    chat_session: ChatSession,
    messages: list[ChatMessage],
    recent_window: int,
    max_summary_chars: int,
) -> None:
    """Deterministically refresh the summary when the cutoff is stale.

    A refresh happens when the newest message beyond the recent window has
    an id greater than the stored summary_cutoff_message_id.
    """
    cutoff_idx = len(messages) - recent_window
    if cutoff_idx <= 0:
        return

    cutoff_message = messages[cutoff_idx - 1]

    # Skip refresh if we already summarized up to this point
    if (
        chat_session.summary_cutoff_message_id is not None
        and chat_session.summary_cutoff_message_id >= cutoff_message.id
    ):
        return

    # Build deterministic summary from older messages
    older = messages[:cutoff_idx]
    summary_text = _deterministic_summary(older, max_summary_chars)

    chat_session.conversation_summary = summary_text
    chat_session.summary_cutoff_message_id = cutoff_message.id
    chat_session.summary_updated_at = datetime.utcnow()

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    logger.debug(
        "Refreshed summary for session %s: cutoff_message_id=%s, summary_len=%d",
        chat_session.id,
        cutoff_message.id,
        len(summary_text),
    )


def _deterministic_summary(messages: list[ChatMessage], max_chars: int) -> str:
    """Build a concise role-prefixed summary from messages, no LLM.

    Each message becomes a single line: "role: truncated_content".
    Lines are trimmed to fit within max_chars.
    """
    lines: list[str] = []
    for msg in messages:
        # Truncate individual message content to ~120 chars
        content = msg.content.replace("\n", " ").strip()
        if len(content) > 120:
            content = content[:117] + "..."
        lines.append(f"{msg.role}: {content}")

    text = "\n".join(lines)

    # Hard-trim to max_chars if needed
    if len(text) > max_chars:
        text = text[: max_chars - 3] + "..."

    return text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_ordered_messages(db: Session, session_id: int) -> list[ChatMessage]:
    """Get all messages for a session in chronological order."""
    return list(
        db.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
        ).all()
    )


def _message_to_dict(msg: ChatMessage) -> dict:
    """Convert a ChatMessage to a plain dict for the context window."""
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
    }
