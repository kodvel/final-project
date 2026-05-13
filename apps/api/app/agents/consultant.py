"""Company Strategy Consultant agent orchestration.

Implements the single CompanyStrategyConsultant agent using OpenAI Agents SDK
with LitellmModel. Handles pre-retrieval classification, tool orchestration,
stream event conversion to DeltaKit SSE, citation persistence, and fallback
when chat model is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generator

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.agents.prompts import PRE_RETRIEVAL_CLASSIFIER_PROMPT, SYSTEM_PROMPT
from app.core.config import get_settings
from app.knowledge.retrieval import EvidenceBundle, SourceScope, retrieve_company_knowledge
from app.models.chat import AgentToolCall, MessageSourceCitation
from app.models.enums import CitationStatus, CitationType
from app.services.context_builder import ContextWindow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types for consultant run results
# ---------------------------------------------------------------------------


@dataclass
class ConsultantEvent:
    """Internal event produced by the consultant before SSE serialization."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CitationRecord:
    """Holds citation data for persistence after the run."""

    citation_type: CitationType
    ordinal: int
    source_id: int | None = None
    artifact_id: int | None = None
    chunk_id: str | None = None
    url: str | None = None
    title: str | None = None
    domain: str | None = None
    provider: str | None = None
    provider_request_id: str | None = None
    published_date: datetime | None = None
    favicon_url: str | None = None
    quote: str | None = None
    snippet: str | None = None
    page_number: int | None = None
    row_refs_json: dict[str, Any] | None = None
    relevance_score: float | None = None
    citation_status: CitationStatus = CitationStatus.AVAILABLE
    retrieved_at: datetime | None = None


@dataclass
class ToolCallRecord:
    """Holds tool call summary for persistence."""

    tool_name: str
    status: str  # success | failed
    summary: str
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None


@dataclass
class ConsultantResult:
    """Complete result of a consultant run."""

    content: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    citations: list[CitationRecord] = field(default_factory=list)
    events: list[ConsultantEvent] = field(default_factory=list)
    unreferenced_context: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Source scope parsing (fix #4)
# ---------------------------------------------------------------------------


# Team label keywords mapping
_TEAM_KEYWORDS: dict[str, str] = {
    "marketing": "marketing",
    "product": "product",
    "data analysis": "data_analysis",
    "data analyst": "data_analysis",
    "analytics": "data_analysis",
    "business": "business",
}

# Category label keywords mapping
_CATEGORY_KEYWORDS: dict[str, str] = {
    "analytics": "analytics_metrics",
    "metrics": "analytics_metrics",
    "market research": "market_research",
    "product feature": "product_feature",
    "product / feature": "product_feature",
    "customer insight": "customer_insight",
    "business model": "business_model",
    "competitor analysis": "competitor_analysis",
    "revenue": "revenue_sales",
    "sales": "revenue_sales",
}

# Month pattern
_MONTH_RE = re.compile(r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}", re.IGNORECASE)
_YYYYMM_RE = re.compile(r"\b(\d{4})-(0[1-9]|1[0-2])\b")


def parse_source_scope(message: str) -> SourceScope | None:
    """Parse natural-language source scope constraints from a user message.

    Minimal deterministic parser that extracts team_label, category_labels,
    period months, and source-specific references. Returns None if no scope
    constraints are detected.
    """
    lower = message.lower()
    parts: dict[str, Any] = {}
    found_any = False

    # Team label
    for keyword, label in _TEAM_KEYWORDS.items():
        if keyword in lower:
            parts["team_label"] = label
            found_any = True
            break

    # Category labels
    cats: list[str] = []
    for keyword, label in _CATEGORY_KEYWORDS.items():
        if keyword in lower and label not in cats:
            cats.append(label)
            found_any = True
    if cats:
        parts["category_labels"] = cats

    # Period months — look for YYYY-MM patterns
    months = _YYYYMM_RE.findall(lower)
    if months:
        month_strs = [f"{y}-{m}" for y, m in months]
        month_strs.sort()
        parts["period_start_month"] = month_strs[0]
        parts["period_end_month"] = month_strs[-1]
        found_any = True

    if not found_any:
        return None

    return SourceScope(**parts)


# ---------------------------------------------------------------------------
# Pre-retrieval classifier
# ---------------------------------------------------------------------------


class RetrievalClassification(BaseModel):
    """Structured output schema for the pre-retrieval classifier."""

    needs_retrieval: bool = Field(
        description=(
            "True if the message requires retrieval of uploaded company Sources "
            "to answer well (company data, metrics, strategy, analysis, etc.). "
            "False only for simple greetings, chitchat, off-topic, or meta-questions."
        ),
    )
    reason: str | None = Field(
        default=None,
        description="Short explanation of why retrieval is or is not needed.",
    )


def classify_needs_retrieval(
    context: ContextWindow,
    current_message: str,
) -> bool:
    """Use OpenAI structured-output classifier to decide if local Source retrieval is needed.

    Uses RAG_* config (rag_openai_api_base_url/key/model) via the ``openai`` SDK
    ``client.chat.completions.parse`` with a Pydantic ``response_format``.
    Classifier failure defaults to True (retrieve by default).
    """
    settings = get_settings()

    if not settings.rag_openai_api_key:
        logger.debug("No RAG API key; defaulting to retrieval")
        return True

    try:
        from openai import OpenAI

        recent_text = ""
        for msg in context.recent_messages[-3:]:
            recent_text += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"

        prompt = PRE_RETRIEVAL_CLASSIFIER_PROMPT.format(
            conversation_summary=context.conversation_summary or "(no summary yet)",
            recent_messages=recent_text.strip() or "(no recent messages)",
            current_message=current_message,
        )

        client = OpenAI(
            base_url=settings.rag_openai_api_base_url,
            api_key=settings.rag_openai_api_key,
        )

        response = client.chat.completions.parse(
            model=settings.rag_openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=RetrievalClassification,
            max_tokens=100,
            temperature=0.0,
        )

        parsed: RetrievalClassification | None = response.choices[0].message.parsed
        if parsed is None:
            logger.warning("Classifier returned no parsed structured output; defaulting to retrieval")
            return True

        logger.debug(
            "Classifier response: needs_retrieval=%s reason=%s",
            parsed.needs_retrieval,
            parsed.reason,
        )
        return parsed.needs_retrieval

    except Exception:
        logger.warning("Classifier failed; defaulting to retrieval", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# Agent function tools (fix #2)
# ---------------------------------------------------------------------------


def _make_retrieve_tool(db: Session, workspace_id: int):
    """Create a retrieve_company_knowledge function tool closed over db/workspace."""

    def retrieve_company_knowledge_fn(query: str, source_scope: dict | None = None) -> str:
        """Retrieve company knowledge evidence from uploaded Sources.

        Searches indexed source_content chunks via vector search, validates
        against SQL, and returns citation-ready evidence. Use this tool whenever
        you need factual data from uploaded company Sources to answer a question.

        Args:
            query: Natural language query for semantic search.
            source_scope: Optional scope filters as JSON object with keys:
                team_label, category_labels, period_start_month,
                period_end_month, source_ids.

        Returns:
            JSON string with compact evidence items and metadata.
        """
        scope = None
        if source_scope:
            scope = SourceScope(
                team_label=source_scope.get("team_label"),
                category_labels=source_scope.get("category_labels"),
                period_start_month=source_scope.get("period_start_month"),
                period_end_month=source_scope.get("period_end_month"),
                source_ids=source_scope.get("source_ids"),
            )
        bundle = retrieve_company_knowledge(db, workspace_id, query, scope)
        # Return compact JSON string — no raw huge output
        items = []
        for item in bundle.items:
            items.append({
                "citation_id": item.citation_id,
                "source_title": item.source_title,
                "file_type": item.file_type,
                "quote": item.quote[:500] if item.quote else "",
                "page_number": item.page_number,
                "relevance_score": item.relevance_score,
            })
        return json.dumps({
            "items": items,
            "insufficient_evidence": bundle.insufficient_evidence,
            "reason": bundle.reason,
            "candidate_count": bundle.candidate_count,
        })

    return retrieve_company_knowledge_fn


def _make_tavily_tool():
    """Create a tavily_web_search function tool."""

    def tavily_web_search_fn(query: str, max_results: int = 5) -> str:
        """Search the web using Tavily for public, current, web-answerable information.

        IMPORTANT RESTRICTIONS:
        - Use ONLY when uploaded Source evidence is weak or empty.
        - Use ONLY for questions about public market data, industry trends,
          competitor public information, or generally available web knowledge.
        - NEVER use to replace uploaded Sources for internal company facts.
        - NEVER use for source-specific internal questions (team metrics, product
          data, customer insights that should come from uploaded Sources).
        - Web evidence must be clearly labeled as "Web Source" in your response.

        Args:
            query: Search query for public/web information.
            max_results: Maximum number of results (default 5).

        Returns:
            JSON string with search results including title, url, content, score.
        """
        from app.core.config import get_settings

        settings = get_settings()
        api_key = settings.tavily_api_key

        if not api_key:
            return json.dumps({"results": [], "error": "Tavily API key not configured"})

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                include_answer=False,
                include_raw_content=False,
                include_images=False,
            )

            results = []
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500],
                    "score": r.get("score", 0.0),
                })

            return json.dumps({
                "results": results,
                "request_id": response.get("request_id"),
            })
        except Exception as e:
            logger.warning("Tavily search failed: %s", e)
            return json.dumps({"results": [], "error": f"Web search failed: {e}"})

    return tavily_web_search_fn


# ---------------------------------------------------------------------------
# Main consultant run (synchronous generator for SSE)
# ---------------------------------------------------------------------------


def run_consultant_stream(
    db: Session,
    workspace_id: int,
    context: ContextWindow,
    evidence_bundle: EvidenceBundle | None = None,
) -> Generator[tuple[ConsultantEvent, ConsultantResult], None, None]:
    """Run the consultant agent and yield (event, result_accumulator) tuples."""
    settings = get_settings()
    current_message = context.current_user_message or ""
    result = ConsultantResult()

    # --- Build evidence context string ---
    evidence_text = ""
    evidence_items_map: dict[str, dict] = {}
    if evidence_bundle and evidence_bundle.items:
        evidence_text = "\n\n## Evidence Bundle\n\n"
        for idx, item in enumerate(evidence_bundle.items, 1):
            citation_marker = f"[{idx}]"
            evidence_text += f"{citation_marker} Source: {item.source_title} ({item.file_type})"
            if item.page_number:
                evidence_text += f", page {item.page_number}"
            evidence_text += f"\nQuote: {item.quote}\n"
            evidence_text += f"Team: {item.team_label}, Section: {item.document_section}\n\n"
            evidence_items_map[item.citation_id] = {
                "ordinal": idx,
                "item": item,
            }

        if evidence_bundle.insufficient_evidence:
            evidence_text += "\n⚠️ Evidence may be insufficient. Consider web search or clearly state gaps.\n"
    else:
        evidence_text = "\n\n## Evidence Bundle\n\nNo uploaded Source evidence available for this query.\n"

    # --- Build conversation history for the model ---
    history = _build_model_history(context, evidence_text)

    # --- Check if chat model key is available ---
    if not settings.chat_openai_api_key:
        yield from _fallback_run(
            current_message=current_message,
            evidence_bundle=evidence_bundle,
            result=result,
        )
        return

    # --- Use Agents SDK with real function tools ---
    try:
        from agents import Agent, Runner, function_tool
        from agents.extensions.models.litellm_model import LitellmModel

        model = LitellmModel(
            model=settings.chat_openai_model,
            base_url=settings.chat_openai_api_base_url,
            api_key=settings.chat_openai_api_key,
        )

        # Build function tools closed over db/workspace
        retrieve_fn = _make_retrieve_tool(db, workspace_id)
        tavily_fn = _make_tavily_tool()

        retrieve_tool = function_tool(
            retrieve_fn,
            name_override="retrieve_company_knowledge",
            strict_mode=False,
        )
        tavily_tool = function_tool(
            tavily_fn,
            name_override="tavily_web_search",
        )

        agent = Agent(
            name="CompanyStrategyConsultant",
            instructions=SYSTEM_PROMPT,
            model=model,
            tools=[retrieve_tool, tavily_tool],
        )

        run_result = Runner.run_sync(
            starting_agent=agent,
            input=history,
        )

        full_text = run_result.final_output or ""

        # Extract tool calls from run items — stream safe events (fix #5)
        for item in run_result.new_items:
            from agents.items import ToolCallItem, ToolCallOutputItem

            if isinstance(item, ToolCallItem):
                raw = item.raw_item
                tool_name = getattr(raw, "name", "unknown")
                call_id = getattr(raw, "call_id", "")
                result.tool_calls.append(
                    ToolCallRecord(
                        tool_name=tool_name,
                        status="success",
                        summary=f"Called {tool_name}",
                    )
                )
                # Only tool_name and call_id streamed, no args/raw/reasoning
                yield (
                    ConsultantEvent(
                        type="tool_call",
                        data={"tool_name": tool_name, "call_id": call_id},
                    ),
                    result,
                )

            elif isinstance(item, ToolCallOutputItem):
                raw = getattr(item, "raw_item", None)
                call_id = getattr(raw, "call_id", "") if raw else ""
                status_val = "ok"
                output = getattr(item, "output", None)
                if isinstance(output, str) and "error" in output.lower():
                    status_val = "error"
                # Only status streamed, no args/raw content
                yield (
                    ConsultantEvent(
                        type="tool_result",
                        data={"call_id": call_id, "ok": status_val == "ok"},
                    ),
                    result,
                )

        # Stream text deltas from the full response
        if full_text:
            chunk_size = max(1, len(full_text) // 8)
            for i in range(0, len(full_text), chunk_size):
                delta = full_text[i : i + chunk_size]
                result.content += delta
                yield (
                    ConsultantEvent(type="text_delta", data={"delta": delta}),
                    result,
                )

        # Extract citations from the response
        _extract_citations(
            result=result,
            full_text=full_text,
            evidence_items_map=evidence_items_map,
            evidence_bundle=evidence_bundle,
        )

    except Exception as e:
        logger.exception("Agent run failed, using fallback")
        result.content = ""
        yield from _fallback_run(
            current_message=current_message,
            evidence_bundle=evidence_bundle,
            result=result,
            error=str(e),
        )


def _build_model_history(
    context: ContextWindow,
    evidence_text: str,
) -> list[dict[str, Any]]:
    """Build the message history for the model from context + evidence."""
    messages: list[dict[str, Any]] = []

    if context.conversation_summary:
        messages.append({
            "role": "user",
            "content": f"[Previous conversation context - NOT evidence]:\n{context.conversation_summary}",
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I will use this for context continuity only, not as source-grounded evidence.",
        })

    for msg in context.recent_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    current = context.current_user_message or ""
    full_content = current + evidence_text
    messages.append({"role": "user", "content": full_content})

    return messages


def _extract_citations(
    result: ConsultantResult,
    full_text: str,
    evidence_items_map: dict[str, dict],
    evidence_bundle: EvidenceBundle | None,
) -> None:
    """Extract citations from the response text and add to result."""
    inline_refs = set(re.findall(r"\[(\d+)\]", full_text))

    if inline_refs and evidence_items_map:
        used_ordinals = {int(n) for n in inline_refs}
        for citation_id, info in evidence_items_map.items():
            ordinal = info["ordinal"]
            if ordinal in used_ordinals:
                item = info["item"]
                result.citations.append(
                    CitationRecord(
                        citation_type=CitationType.UPLOADED_SOURCE,
                        ordinal=ordinal,
                        source_id=item.source_id,
                        artifact_id=item.artifact_id,
                        chunk_id=item.chunk_id,
                        title=item.source_title,
                        quote=item.quote,
                        page_number=item.page_number,
                        row_refs_json=item.row_refs if isinstance(item.row_refs, dict) else None,
                        relevance_score=item.relevance_score,
                        citation_status=CitationStatus.AVAILABLE,
                        retrieved_at=datetime.utcnow(),
                    )
                )
    elif evidence_bundle and evidence_bundle.items:
        for item in evidence_bundle.items[:3]:
            result.unreferenced_context.append({
                "source_title": item.source_title,
                "quote": item.quote[:200],
                "relevance_score": item.relevance_score,
            })


def _fallback_run(
    current_message: str,
    evidence_bundle: EvidenceBundle | None,
    result: ConsultantResult,
    error: str | None = None,
) -> Generator[tuple[ConsultantEvent, ConsultantResult], None, None]:
    """Produce a grounded gap/fallback response when the chat model is unavailable."""
    has_evidence = evidence_bundle and evidence_bundle.items and not evidence_bundle.insufficient_evidence

    if has_evidence and evidence_bundle is not None:
        sources = set(item.source_title for item in evidence_bundle.items[:3])
        source_list = ", ".join(sources)
        response = (
            "I can see relevant uploaded Source data, but the AI "
            "consultant model is currently unavailable. Here is what I found from your Sources.\n\n"
            f"Found evidence from: {source_list}. "
            f"{evidence_bundle.items[0].quote[:200]}...\n\n"
            "The AI model service needs to be configured "
            "or is temporarily unavailable. Please try again later.\n\n"
            "Confidence: Low — AI model unavailable. "
            "Evidence was retrieved but not interpreted.\n\n"
            "Gaps: Full AI interpretation is not available. "
            "The raw evidence above may be useful, but lacks strategic analysis."
        )

        for idx, item in enumerate(evidence_bundle.items[:3], 1):
            result.citations.append(
                CitationRecord(
                    citation_type=CitationType.UPLOADED_SOURCE,
                    ordinal=idx,
                    source_id=item.source_id,
                    artifact_id=item.artifact_id,
                    chunk_id=item.chunk_id,
                    title=item.source_title,
                    quote=item.quote,
                    page_number=item.page_number,
                    relevance_score=item.relevance_score,
                    citation_status=CitationStatus.AVAILABLE,
                    retrieved_at=datetime.utcnow(),
                )
            )
    else:
        insufficient_reason = ""
        if evidence_bundle:
            insufficient_reason = f" Reason: {evidence_bundle.reason or 'insufficient'}"

        error_detail = ""
        if error:
            error_detail = f"The AI service encountered an error: {error[:100]}. "
        else:
            error_detail = "The AI model is not currently configured. "

        response = (
            "I was unable to process your question fully.\n\n"
            "No sufficient uploaded Source evidence available."
            f"{insufficient_reason}\n\n"
            f"{error_detail}"
            "Upload and process relevant Sources first, then try again. "
            "If this persists, check the AI configuration.\n\n"
            "Confidence: Low — AI model unavailable or insufficient evidence.\n\n"
            "Gaps: "
        )
        if evidence_bundle and evidence_bundle.insufficient_evidence:
            response += "Retrieved evidence was insufficient. "
        if not evidence_bundle or not evidence_bundle.items:
            response += "No evidence was found for this query. "
        response += "Consider uploading more relevant Sources."

    # Stream the fallback response as text deltas
    chunk_size = max(1, len(response) // 6)
    for i in range(0, len(response), chunk_size):
        delta = response[i : i + chunk_size]
        result.content += delta
        yield (
            ConsultantEvent(type="text_delta", data={"delta": delta}),
            result,
        )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def persist_tool_calls(
    db: Session,
    message_id: int,
    tool_calls: list[ToolCallRecord],
) -> list[AgentToolCall]:
    """Persist tool call records for an assistant message."""
    records = []
    for tc in tool_calls:
        record = AgentToolCall(
            message_id=message_id,
            tool_name=tc.tool_name,
            status=tc.status,
            summary=tc.summary,
            input_json=tc.input_json,
            output_json=tc.output_json,
        )
        db.add(record)
        records.append(record)
    if records:
        db.flush()
    return records


def persist_citations(
    db: Session,
    message_id: int,
    citations: list[CitationRecord],
) -> list[MessageSourceCitation]:
    """Persist citation records for an assistant message."""
    records = []
    for cit in citations:
        record = MessageSourceCitation(
            message_id=message_id,
            citation_type=cit.citation_type,
            ordinal=cit.ordinal,
            source_id=cit.source_id,
            artifact_id=cit.artifact_id,
            chunk_id=cit.chunk_id,
            url=cit.url,
            title=cit.title,
            domain=cit.domain,
            provider=cit.provider,
            provider_request_id=cit.provider_request_id,
            published_date=cit.published_date,
            favicon_url=cit.favicon_url,
            quote=cit.quote,
            snippet=cit.snippet,
            page_number=cit.page_number,
            row_refs_json=cit.row_refs_json,
            relevance_score=cit.relevance_score,
            citation_status=cit.citation_status,
            retrieved_at=cit.retrieved_at or datetime.utcnow(),
        )
        db.add(record)
        records.append(record)
    if records:
        db.flush()
    return records


def persist_web_citations(
    db: Session,
    message_id: int,
    web_results: list[dict],
    start_ordinal: int = 1,
) -> list[MessageSourceCitation]:
    """Persist web search results as citations."""
    records = []
    for idx, r in enumerate(web_results, start=start_ordinal):
        record = MessageSourceCitation(
            message_id=message_id,
            citation_type=CitationType.WEB,
            ordinal=idx,
            url=r.get("url"),
            title=r.get("title"),
            domain=_extract_domain(r.get("url", "")),
            provider="tavily",
            provider_request_id=r.get("request_id"),
            snippet=r.get("content"),
            relevance_score=r.get("score"),
            citation_status=CitationStatus.AVAILABLE,
            retrieved_at=datetime.utcnow(),
        )
        db.add(record)
        records.append(record)
    if records:
        db.flush()
    return records


def _extract_domain(url: str) -> str | None:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None
