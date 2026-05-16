"""Decision Brief draft orchestration.

Task 8: generate a structured Decision Brief Draft from the current Chat Session
        using a deterministic structured-output LLM workflow over the session's
        messages and already-used citations.

Task 9: transition the brief's approval status through a small state machine.
        On approval, the brief content is indexed into ChromaDB so future
        sessions in the same workspace can retrieve it as evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc
from sqlmodel import Session, select

from app.models.chat import ChatMessage, ChatSession, MessageSourceCitation
from app.models.decision_brief import DecisionBrief
from app.models.enums import (
    ChatMessageRole,
    DecisionApprovalStatus,
    DecisionRecommendationStatus,
)
from app.schemas.decision_brief import DecisionBriefContent
from app.services.context_builder import build_context

logger = logging.getLogger(__name__)


INSUFFICIENT_CONTEXT_MESSAGE = (
    "Belum ada context yang cukup untuk membuat Decision Brief Draft.\n"
    "Diskusikan keputusan, opsi, risiko, dan evidence terlebih dahulu, lalu "
    "jalankan /decision-brief lagi."
)


@dataclass
class InsufficientContext:
    """Marker returned when the session is too sparse to draft a brief."""

    message: str = INSUFFICIENT_CONTEXT_MESSAGE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_sufficient_context(
    messages: list[ChatMessage],
    citations: list[MessageSourceCitation],
) -> bool:
    assistant_turns = sum(
        1 for m in messages if m.role == ChatMessageRole.ASSISTANT and m.content.strip()
    )
    return assistant_turns >= 1 and len(citations) >= 1


def _resolve_recommendation_status(
    content: DecisionBriefContent,
    citations: list[MessageSourceCitation],
) -> DecisionRecommendationStatus:
    """Clamp the model's recommendation to validate_first when evidence is weak."""
    valid_ordinals = {c.ordinal for c in citations if c.ordinal is not None}
    referenced = {ref.ordinal for ref in content.source_evidence}
    used_valid = referenced & valid_ordinals
    if not used_valid or content.risks_assumptions:
        # Either evidence is unreferenced or risks are explicitly flagged.
        if not used_valid:
            return DecisionRecommendationStatus.VALIDATE_FIRST
    return content.recommendation_status


def _next_sequence_number(db: Session, session_id: int) -> int:
    existing = db.exec(
        select(DecisionBrief.sequence_number)
        .where(DecisionBrief.chat_session_id == session_id)
        .order_by(desc(DecisionBrief.sequence_number))
    ).first()
    return (existing or 0) + 1


def _filter_evidence_refs(
    content: DecisionBriefContent,
    citations: list[MessageSourceCitation],
) -> DecisionBriefContent:
    """Drop evidence refs whose ordinal isn't in the session's citation set."""
    valid_ordinals = {c.ordinal for c in citations if c.ordinal is not None}
    content.source_evidence = [
        ref for ref in content.source_evidence if ref.ordinal in valid_ordinals
    ]
    return content


def _build_brief_content_json(content: DecisionBriefContent) -> dict:
    return content.model_dump()


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------


def generate_decision_brief(
    db: Session,
    chat_session: ChatSession,
    user_message: ChatMessage,
) -> DecisionBrief | InsufficientContext:
    """Generate a Decision Brief Draft for the given Chat Session.

    Returns either the persisted ``DecisionBrief`` row, or
    ``InsufficientContext`` when the session does not yet have enough material.
    """
    from app.services.chat import list_citations_for_session, list_messages

    messages = list_messages(db, chat_session.id)
    # Exclude the current /decision-brief user message from "assistant turns" count.
    prior_messages = [m for m in messages if m.id != user_message.id]
    citations = list_citations_for_session(db, chat_session.id)

    if not _has_sufficient_context(prior_messages, citations):
        return InsufficientContext()

    from app.agents.decision_brief import generate_brief_content

    context = build_context(db, chat_session, current_user_message=None)
    content = generate_brief_content(
        chat_session=chat_session,
        prior_messages=prior_messages,
        citations=citations,
        conversation_summary=context.conversation_summary,
        recent_messages=context.recent_messages,
    )

    content = _filter_evidence_refs(content, citations)
    recommendation_status = _resolve_recommendation_status(content, citations)

    sequence_number = _next_sequence_number(db, chat_session.id)
    context_cutoff_message_id = prior_messages[-1].id if prior_messages else user_message.id

    # Create the assistant Decision Brief message.
    from app.models.enums import ChatMessageType, MessageStatus

    now = datetime.utcnow()
    assistant_msg = ChatMessage(
        session_id=chat_session.id,
        role=ChatMessageRole.ASSISTANT,
        content=content.title,
        message_type=ChatMessageType.DECISION_BRIEF,
        status=MessageStatus.COMPLETED,
        completed_at=now,
        updated_at=now,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    brief = DecisionBrief(
        workspace_id=chat_session.workspace_id,
        chat_session_id=chat_session.id,
        chat_message_id=assistant_msg.id,
        sequence_number=sequence_number,
        context_cutoff_message_id=context_cutoff_message_id,
        title=content.title,
        objective=content.objective,
        recommendation_status=recommendation_status,
        approval_status=DecisionApprovalStatus.DRAFT,
        content_json=_build_brief_content_json(content),
        created_at=now,
        updated_at=now,
        status_updated_at=now,
    )
    db.add(brief)
    chat_session.last_message_at = now
    chat_session.updated_at = now
    db.add(chat_session)
    db.commit()
    db.refresh(brief)
    return brief


# ---------------------------------------------------------------------------
# Status transitions (Task 9)
# ---------------------------------------------------------------------------


_VALID_TRANSITIONS: dict[DecisionApprovalStatus, set[DecisionApprovalStatus]] = {
    DecisionApprovalStatus.DRAFT: {
        DecisionApprovalStatus.REVIEWED,
        DecisionApprovalStatus.APPROVED,
        DecisionApprovalStatus.REJECTED,
    },
    DecisionApprovalStatus.REVIEWED: {
        DecisionApprovalStatus.APPROVED,
        DecisionApprovalStatus.REJECTED,
    },
    DecisionApprovalStatus.APPROVED: set(),
    DecisionApprovalStatus.REJECTED: set(),
}


class InvalidStatusTransition(ValueError):
    """Raised when attempting an invalid approval-status transition."""


def transition_status(
    db: Session,
    brief: DecisionBrief,
    new_status: DecisionApprovalStatus,
) -> DecisionBrief:
    """Move a Decision Brief through the approval state machine.

    Raises:
        InvalidStatusTransition: if the requested move is not allowed.
    """
    current = brief.approval_status
    if new_status == current:
        return brief

    allowed = _VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise InvalidStatusTransition(
            f"Cannot transition Decision Brief from {current.value} to {new_status.value}"
        )

    now = datetime.utcnow()
    brief.approval_status = new_status
    brief.status_updated_at = now
    brief.updated_at = now
    db.add(brief)
    db.commit()
    db.refresh(brief)

    if new_status == DecisionApprovalStatus.APPROVED:
        try:
            from app.knowledge.indexing import index_decision_brief

            index_decision_brief(brief)
        except Exception:
            logger.exception(
                "Failed to index approved Decision Brief %s into knowledge collection",
                brief.id,
            )

    return brief
