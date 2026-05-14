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

from app.core.config import get_settings
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


SYSTEM_PROMPT = """You are a senior strategy consultant generating a Decision Brief Draft.

You will receive a chat conversation (summary + recent messages) and a list of \
citations already used in that conversation. Produce a structured Decision Brief \
that reuses ONLY those citations as evidence — do not invent new sources.

Rules:
- Reference evidence by the citation ordinal exactly as provided (1-indexed).
- If evidence is weak or contradictory, set recommendation_status to \
"validate_first" and list the evidence gaps under risks_assumptions.
- Be concrete: alternatives_considered, risks_assumptions, success_metrics, \
and next_steps should each be a short bulleted-style list (one idea per item).
- objective is a single paragraph framing the decision under consideration.
- Do not include any text outside the structured fields.
"""


@dataclass
class InsufficientContext:
    """Marker returned when the session is too sparse to draft a brief."""

    message: str = INSUFFICIENT_CONTEXT_MESSAGE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_citation_for_prompt(citation: MessageSourceCitation) -> str:
    ordinal = citation.ordinal or 0
    kind = "Web" if citation.citation_type.value == "web" else "Uploaded"
    parts: list[str] = [f"[{ordinal}] ({kind})"]
    if citation.title:
        parts.append(citation.title)
    if citation.url:
        parts.append(citation.url)
    if citation.page_number is not None:
        parts.append(f"p.{citation.page_number}")
    if citation.quote:
        snippet = citation.quote.strip().replace("\n", " ")
        if len(snippet) > 280:
            snippet = snippet[:277] + "..."
        parts.append(f"\"{snippet}\"")
    elif citation.snippet:
        snippet = citation.snippet.strip().replace("\n", " ")
        if len(snippet) > 280:
            snippet = snippet[:277] + "..."
        parts.append(f"\"{snippet}\"")
    return " — ".join(parts)


def _build_prompt(
    session: ChatSession,
    messages: list[ChatMessage],
    citations: list[MessageSourceCitation],
    summary: str | None,
    recent_messages: list[dict],
) -> str:
    """Compose the user content for the structured LLM call."""
    lines: list[str] = [f"Chat Session: {session.title}"]
    if summary:
        lines.append("")
        lines.append("Conversation summary (older messages):")
        lines.append(summary)

    lines.append("")
    lines.append("Recent conversation:")
    for msg in recent_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"  {role}: {content}")

    if citations:
        lines.append("")
        lines.append("Citations already used in this session:")
        for citation in citations:
            lines.append(f"  {_format_citation_for_prompt(citation)}")
    else:
        lines.append("")
        lines.append("Citations already used: (none)")

    lines.append("")
    lines.append(
        "Produce a Decision Brief Draft as a structured JSON object. "
        "Reference evidence by ordinal only."
    )
    return "\n".join(lines)


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

    context = build_context(db, chat_session, current_user_message=None)
    prompt = _build_prompt(
        chat_session,
        prior_messages,
        citations,
        context.conversation_summary,
        context.recent_messages,
    )

    settings = get_settings()
    if not settings.rag_openai_api_key:
        # Generate a minimal deterministic stub when no API key is configured.
        # Used for tests and demo environments without LLM credentials.
        content = _deterministic_fallback(chat_session, citations)
    else:
        from app.services.langfuse_openai import create_openai_client
        from app.services.llm_extraction import extract_structured

        client = create_openai_client(
            base_url=settings.rag_openai_api_base_url,
            api_key=settings.rag_openai_api_key,
        )
        try:
            content = extract_structured(
                client=client,
                model=settings.rag_openai_model,
                system_prompt=SYSTEM_PROMPT,
                user_content=prompt,
                response_format=DecisionBriefContent,
                temperature=0.2,
                retries=1,
                name="decision_brief.generate",
                metadata={"stage": "decision_brief.generate", "session_id": str(chat_session.id)},
            )
        except Exception:
            logger.exception("Decision brief extraction failed; using deterministic fallback")
            content = _deterministic_fallback(chat_session, citations)

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


# ---------------------------------------------------------------------------
# Deterministic fallback (no LLM)
# ---------------------------------------------------------------------------


def _deterministic_fallback(
    chat_session: ChatSession,
    citations: list[MessageSourceCitation],
) -> DecisionBriefContent:
    """Produce a minimal brief without LLM access — keeps tests and demos working."""
    from app.schemas.decision_brief import DecisionBriefEvidenceRef

    refs = [
        DecisionBriefEvidenceRef(ordinal=c.ordinal, note=c.title or c.quote or None)
        for c in citations
        if c.ordinal is not None
    ]
    return DecisionBriefContent(
        title=f"Decision Brief — {chat_session.title}",
        objective="Draft generated without LLM access. Review with the team before acting.",
        context_problem="(auto-generated stub — LLM not configured)",
        source_evidence=refs,
        strategic_interpretation="Refer to cited evidence for the strategic picture.",
        recommendation="Validate the assumptions with the team before proceeding.",
        alternatives_considered=[],
        risks_assumptions=["LLM not configured; brief contents are placeholders."],
        success_metrics=[],
        next_steps=["Re-run /decision-brief once an LLM is configured."],
        recommendation_status=DecisionRecommendationStatus.VALIDATE_FIRST,
    )
