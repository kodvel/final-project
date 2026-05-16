"""Decision Brief generation agent.

Given a chat session's prior messages and used citations, produce a structured
``DecisionBriefContent`` via the LLM (with a deterministic fallback when no
LLM API key is configured or the call fails).

The service layer (:mod:`app.services.decision_briefs`) handles persistence,
sequence numbering, status transitions, and indexing — this module only owns
the prompt construction and LLM call.
"""

from __future__ import annotations

import logging

from app.agents.extraction import extract_structured
from app.agents.prompt_registry import load_prompt
from app.agents.prompts import DECISION_BRIEF_SYSTEM_PROMPT
from app.core.config import get_settings
from app.models.chat import ChatMessage, ChatSession, MessageSourceCitation
from app.models.enums import DecisionRecommendationStatus
from app.schemas.decision_brief import DecisionBriefContent, DecisionBriefEvidenceRef

logger = logging.getLogger(__name__)


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


def _build_user_content(
    session: ChatSession,
    messages: list[ChatMessage],
    citations: list[MessageSourceCitation],
    summary: str | None,
    recent_messages: list[dict],
) -> str:
    """Compose the user message that pairs with the system prompt."""
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


def _deterministic_fallback(
    chat_session: ChatSession,
    citations: list[MessageSourceCitation],
) -> DecisionBriefContent:
    """Produce a minimal brief without LLM access — keeps tests and demos working."""
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


def generate_brief_content(
    chat_session: ChatSession,
    prior_messages: list[ChatMessage],
    citations: list[MessageSourceCitation],
    conversation_summary: str | None,
    recent_messages: list[dict],
) -> DecisionBriefContent:
    """Run the decision-brief LLM (or fallback) and return structured content.

    Falls back to a deterministic stub when no LLM API key is configured or
    when the LLM call raises — the caller still gets a usable
    ``DecisionBriefContent`` in either case.
    """
    settings = get_settings()
    if not settings.rag_openai_api_key:
        return _deterministic_fallback(chat_session, citations)

    from app.core.openai_client import create_openai_client

    user_content = _build_user_content(
        chat_session,
        prior_messages,
        citations,
        conversation_summary,
        recent_messages,
    )
    client = create_openai_client(
        base_url=settings.rag_openai_api_base_url,
        api_key=settings.rag_openai_api_key,
    )
    try:
        system = load_prompt("decision-brief-system", DECISION_BRIEF_SYSTEM_PROMPT)
        return extract_structured(
            client=client,
            model=settings.rag_generation_model,
            system_prompt=system.text,
            user_content=user_content,
            response_format=DecisionBriefContent,
            temperature=0.2,
            retries=1,
            name="decision_brief.generate",
            metadata={"stage": "decision_brief.generate", "session_id": str(chat_session.id)},
            langfuse_prompt=system.langfuse_prompt,
        )
    except Exception:
        logger.exception("Decision brief extraction failed; using deterministic fallback")
        return _deterministic_fallback(chat_session, citations)


__all__ = ["generate_brief_content"]
