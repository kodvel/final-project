"""Decision Brief Draft generation service.

Pipeline:
  1. Load all messages + session citations.
  2. Guard: insufficient context → return command_result message, no brief.
  3. LLM call: extract decision context → draft structured content_json.
  4. Validate citation IDs in code.
  5. Persist DecisionBrief row + assistant ChatMessage (message_type=decision_brief).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from sqlmodel import Session, func, select

from app.core.config import get_settings
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

logger = logging.getLogger(__name__)

INSUFFICIENT_CONTEXT_MSG = (
    "Belum ada context yang cukup untuk membuat Decision Brief Draft.\n"
    "Diskusikan keputusan, opsi, risiko, dan evidence terlebih dahulu, lalu jalankan /decision-brief lagi."
)

_EXTRACT_SYSTEM_PROMPT = """You are a strategic decision analyst. Given a chat conversation and its citations, extract and draft a structured Decision Brief in JSON.

Respond ONLY with valid JSON matching exactly this schema:
{
  "title": "short decision title (max 80 chars)",
  "objective": "one-sentence decision objective",
  "recommendation_status": "go | no_go | validate_first",
  "content_json": {
    "context_problem": "What decision needs to be made and why",
    "source_evidence": "Key evidence from cited sources supporting this decision",
    "strategic_interpretation": "Strategic meaning and implications of the evidence",
    "recommendation": "Clear recommendation with rationale",
    "alternatives_considered": "Other options that were discussed or evaluated",
    "risks_assumptions": "Key risks and assumptions underlying this decision",
    "success_metrics": "How success will be measured",
    "next_steps": "Immediate concrete actions to take"
  },
  "cited_chunk_ids": ["list of citation chunk_ids or citation IDs used as evidence"]
}

Rules:
- Set recommendation_status to "validate_first" if evidence is weak, missing, or contradictory.
- Set "go" only when evidence clearly supports the decision.
- Set "no_go" only when evidence clearly advises against.
- cited_chunk_ids must only reference IDs from the provided citations list.
- Write in professional but accessible language. Be specific and actionable.
- If there is no clear decision topic from the conversation, set recommendation_status to "validate_first" and note the gap in context_problem."""


def _call_llm(system_prompt: str, user_content: str) -> str:
    import litellm

    settings = get_settings()
    response = litellm.completion(
        model=f"openai/{settings.rag_openai_model}",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        api_base=settings.rag_openai_api_base_url,
        api_key=settings.rag_openai_api_key,
        temperature=0.2,
    )
    return response.choices[0].message.content


def _parse_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    fixed = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


def _build_conversation_text(messages: list[ChatMessage]) -> str:
    parts = []
    for msg in messages:
        role = "User" if msg.role == ChatMessageRole.USER else "Assistant"
        parts.append(f"{role}: {msg.content}")
    return "\n\n".join(parts)


def _build_citations_text(citations: list[MessageSourceCitation]) -> str:
    if not citations:
        return "No citations available."
    lines = []
    for c in citations:
        if c.citation_type == CitationType.WEB:
            lines.append(f"- [web:{c.id}] {c.title or c.domain or c.url} — {c.snippet or c.quote or ''}")
        else:
            chunk_ref = c.chunk_id or str(c.id)
            lines.append(f"- [chunk:{chunk_ref}] Source: {c.title or f'Source #{c.source_id}'} | Quote: {(c.quote or '')[:200]}")
    return "\n".join(lines)


def _validate_chunk_ids(cited_ids: list[str], citations: list[MessageSourceCitation]) -> list[str]:
    valid_chunk_ids = {c.chunk_id for c in citations if c.chunk_id}
    valid_citation_ids = {str(c.id) for c in citations}
    return [cid for cid in cited_ids if cid in valid_chunk_ids or cid in valid_citation_ids]


def _next_sequence_number(db: Session, session_id: int) -> int:
    result = db.exec(
        select(func.count(DecisionBrief.id)).where(DecisionBrief.chat_session_id == session_id)
    ).one()
    return (result or 0) + 1


def generate_decision_brief(
    db: Session,
    workspace_id: int,
    session_id: int,
) -> tuple[ChatMessage, DecisionBrief | None]:
    """Generate a Decision Brief Draft from the current Chat Session.

    Returns (assistant_message, decision_brief). If context is insufficient,
    decision_brief is None and assistant_message has message_type=command_result.
    """
    chat_session = db.exec(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.workspace_id == workspace_id,
        )
    ).first()
    if chat_session is None:
        raise ValueError(f"Chat Session {session_id} not found for workspace {workspace_id}")

    # Load all messages for full-session context
    messages = list(db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
    ).all())

    # Load all session citations
    message_ids = [m.id for m in messages if m.id is not None]
    citations: list[MessageSourceCitation] = []
    if message_ids:
        citations = list(db.exec(
            select(MessageSourceCitation).where(
                MessageSourceCitation.message_id.in_(message_ids)
            )
        ).all())

    # Guard: need at least a meaningful conversation with an assistant reply
    non_empty_messages = [m for m in messages if m.content.strip()]
    has_assistant_response = any(m.role == ChatMessageRole.ASSISTANT for m in non_empty_messages)

    if len(non_empty_messages) < 2 or not has_assistant_response:
        now = datetime.utcnow()
        assistant_msg = ChatMessage(
            session_id=session_id,
            role=ChatMessageRole.ASSISTANT,
            content=INSUFFICIENT_CONTEXT_MSG,
            message_type=ChatMessageType.COMMAND_RESULT,
            status=MessageStatus.COMPLETED,
            completed_at=now,
            updated_at=now,
        )
        db.add(assistant_msg)
        chat_session.last_message_at = now
        chat_session.updated_at = now
        db.add(chat_session)
        db.commit()
        db.refresh(assistant_msg)
        return assistant_msg, None

    # Build LLM input — use all messages for full-session awareness
    conversation_text = _build_conversation_text(non_empty_messages)
    citations_text = _build_citations_text(citations)
    context_cutoff_message_id = max((m.id for m in messages if m.id is not None), default=None)

    user_content = (
        f"CONVERSATION:\n{conversation_text}\n\n"
        f"CITED SOURCES AND EVIDENCE:\n{citations_text}\n\n"
        "Generate the Decision Brief Draft JSON now."
    )

    # LLM call with one retry
    parsed: dict | None = None
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            raw = _call_llm(_EXTRACT_SYSTEM_PROMPT, user_content)
            parsed = _parse_json(raw)
            if parsed is not None:
                break
        except Exception as exc:
            last_err = exc
            if attempt == 0:
                logger.warning("Decision brief LLM call failed (attempt 1), retrying: %s", exc)

    if parsed is None:
        raise RuntimeError(f"Decision brief generation failed: {last_err or 'JSON parse error'}")

    # Validate citation IDs in code (never trust LLM-generated IDs)
    raw_cited = parsed.get("cited_chunk_ids", [])
    valid_cited = _validate_chunk_ids(raw_cited if isinstance(raw_cited, list) else [], citations)

    # Determine recommendation_status
    rec_raw = str(parsed.get("recommendation_status", "validate_first")).strip().lower()
    if rec_raw == "go":
        rec_status = DecisionRecommendationStatus.GO
    elif rec_raw == "no_go":
        rec_status = DecisionRecommendationStatus.NO_GO
    else:
        rec_status = DecisionRecommendationStatus.VALIDATE_FIRST

    # Weak-evidence safety: if no citations at all, can't be GO
    if not citations and rec_status == DecisionRecommendationStatus.GO:
        rec_status = DecisionRecommendationStatus.VALIDATE_FIRST

    content_json: dict = parsed.get("content_json", {})
    for section in (
        "context_problem", "source_evidence", "strategic_interpretation",
        "recommendation", "alternatives_considered", "risks_assumptions",
        "success_metrics", "next_steps",
    ):
        content_json.setdefault(section, "")

    title = str(parsed.get("title", "Decision Brief"))[:80]
    objective = parsed.get("objective") or None
    sequence_number = _next_sequence_number(db, session_id)

    # Format assistant message content as readable markdown
    rec_label = {"go": "GO ✓", "no_go": "NO GO ✗", "validate_first": "VALIDATE FIRST ⚠"}.get(
        rec_status.value, rec_status.value.upper()
    )
    content_lines = [
        f"## Decision Brief Draft #{sequence_number}: {title}",
        "",
        f"**Recommendation:** {rec_label}",
    ]
    if objective:
        content_lines += [f"**Objective:** {objective}", ""]
    else:
        content_lines.append("")

    section_labels = [
        ("context_problem", "Context & Problem"),
        ("source_evidence", "Source Evidence"),
        ("strategic_interpretation", "Strategic Interpretation"),
        ("recommendation", "Recommendation"),
        ("alternatives_considered", "Alternatives Considered"),
        ("risks_assumptions", "Risks & Assumptions"),
        ("success_metrics", "Success Metrics"),
        ("next_steps", "Next Steps"),
    ]
    for key, label in section_labels:
        text = content_json.get(key, "").strip()
        if text:
            content_lines += [f"### {label}", text, ""]

    if not citations:
        content_lines.append(
            "_Note: No source evidence was cited in this session. "
            "Consider uploading and discussing relevant Sources before generating a brief._"
        )

    formatted_content = "\n".join(content_lines)
    now = datetime.utcnow()

    # Persist assistant message first (brief links to it)
    assistant_msg = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.ASSISTANT,
        content=formatted_content,
        message_type=ChatMessageType.DECISION_BRIEF,
        status=MessageStatus.COMPLETED,
        metadata_json={
            "brief_sequence_number": sequence_number,
            "recommendation_status": rec_status.value,
            "cited_chunk_ids": valid_cited,
        },
        completed_at=now,
        updated_at=now,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # Persist DecisionBrief row
    brief = DecisionBrief(
        workspace_id=workspace_id,
        chat_session_id=session_id,
        chat_message_id=assistant_msg.id,
        sequence_number=sequence_number,
        title=title,
        objective=objective,
        recommendation_status=rec_status,
        approval_status=DecisionApprovalStatus.DRAFT,
        content_json=content_json,
        context_cutoff_message_id=context_cutoff_message_id,
        status_updated_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(brief)

    chat_session.last_message_at = now
    chat_session.updated_at = now
    db.add(chat_session)
    db.commit()
    db.refresh(brief)

    return assistant_msg, brief
