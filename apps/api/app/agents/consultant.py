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
from typing import Any, AsyncGenerator, Generator

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.agents.prompts import CONSULTANT_SYSTEM_PROMPT, PRE_RETRIEVAL_CLASSIFIER_PROMPT
from app.core.config import get_settings
from app.knowledge.retrieval import EvidenceBundle, SourceScope, retrieve_company_knowledge
from app.models.chat import AgentToolCall, MessageSourceCitation
from app.models.enums import CitationStatus, CitationType
from app.services.context_builder import ContextWindow

logger = logging.getLogger(__name__)


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Get value from dict (.get) or object (getattr), handling both cases."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _next_ordinal(citations: list[CitationRecord]) -> int:
    """Return the next available ordinal: max existing ordinal + 1, or 1 if empty.

    Avoids collisions when ordinals are sparse (e.g. [1, 3] → 4).
    """
    if not citations:
        return 1
    return max(c.ordinal for c in citations) + 1


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
    call_id: str | None = None
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


# Team label patterns.
#
# Only trigger a team filter when the user explicitly scopes the question to a
# team — bare mentions like "product launch" or "marketing campaign" must NOT
# scope retrieval, since they are part of the question content, not a filter.
#
# Accepted phrasings:
#   "marketing team", "the product team"
#   "from the marketing team", "by product", "in marketing team", "for business"
#   "team marketing", "team: product"
_TEAM_LABELS: tuple[tuple[str, str], ...] = (
    ("marketing", "marketing"),
    ("product", "product"),
    ("business", "business"),
    ("data analysis", "data_analysis"),
    ("data analyst", "data_analysis"),
)

_TEAM_SCOPE_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        # "<keyword> team"
        r"\b(marketing|product|business|data\s+analysis|data\s+analyst)\s+team\b",
        # "team <keyword>" / "team: <keyword>"
        r"\bteam[:\s]+(marketing|product|business|data\s+analysis|data\s+analyst)\b",
        # "from/by/in/for [the] <keyword> team"
        r"\b(?:from|by|in|for)\s+(?:the\s+)?(marketing|product|business|data\s+analysis|data\s+analyst)\s+team\b",
        # "tagged <keyword>"
        r"\btagged\s+(marketing|product|business|data\s+analysis|data\s+analyst)\b",
    )
)


def _detect_team_label(lower: str) -> str | None:
    for pattern in _TEAM_SCOPE_PATTERNS:
        match = pattern.search(lower)
        if match:
            raw = re.sub(r"\s+", " ", match.group(1).lower()).strip()
            for keyword, label in _TEAM_LABELS:
                if raw == keyword:
                    return label
    return None


# Category label patterns.
#
# Multi-word category names (e.g. "competitor analysis") are specific enough to
# match as-is. Single-word categories (analytics, metrics, revenue, sales) must
# appear in an explicit scoping phrase to avoid false positives on content
# words.
_MULTIWORD_CATEGORY_KEYWORDS: dict[str, str] = {
    "market research": "market_research",
    "product feature": "product_feature",
    "product / feature": "product_feature",
    "customer insight": "customer_insight",
    "business model": "business_model",
    "competitor analysis": "competitor_analysis",
}

_SINGLEWORD_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("analytics", "analytics_metrics"),
    ("metrics", "analytics_metrics"),
    ("revenue", "revenue_sales"),
    ("sales", "revenue_sales"),
)

_CATEGORY_SCOPE_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        # "<keyword> category" / "<keyword> categories"
        r"\b(analytics|metrics|revenue|sales)\s+categor(?:y|ies)\b",
        # "category: <keyword>" / "categories: <keyword>"
        r"\bcategor(?:y|ies)[:\s]+(analytics|metrics|revenue|sales)\b",
        # "tagged <keyword>"
        r"\btagged\s+(analytics|metrics|revenue|sales)\b",
    )
)


def _detect_category_labels(lower: str) -> list[str]:
    labels: list[str] = []
    for keyword, label in _MULTIWORD_CATEGORY_KEYWORDS.items():
        if keyword in lower and label not in labels:
            labels.append(label)
    for pattern in _CATEGORY_SCOPE_PATTERNS:
        for match in pattern.finditer(lower):
            raw = match.group(1).lower()
            for keyword, label in _SINGLEWORD_CATEGORIES:
                if raw == keyword and label not in labels:
                    labels.append(label)
                    break
    return labels


# Month pattern
_MONTH_RE = re.compile(r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}", re.IGNORECASE)
_YYYYMM_RE = re.compile(r"\b(\d{4})-(0[1-9]|1[0-2])\b")


def parse_source_scope(message: str) -> SourceScope | None:
    """Parse natural-language source scope constraints from a user message.

    Returns None unless the user explicitly scopes by team, category, or
    period. Incidental mentions of category/team words inside the question
    content (e.g. "product launch", "AI analytics") do not trigger a filter.
    """
    lower = message.lower()
    parts: dict[str, Any] = {}
    found_any = False

    team_label = _detect_team_label(lower)
    if team_label is not None:
        parts["team_label"] = team_label
        found_any = True

    cats = _detect_category_labels(lower)
    if cats:
        parts["category_labels"] = cats
        found_any = True

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
        from openai import APIStatusError

        recent_text = ""
        for msg in context.recent_messages[-3:]:
            recent_text += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"

        from app.agents.prompt_registry import load_prompt
        from app.core.openai_client import create_openai_client

        classifier_prompt = load_prompt(
            "consultant-pre-retrieval-classifier",
            PRE_RETRIEVAL_CLASSIFIER_PROMPT,
            conversation_summary=context.conversation_summary or "(no summary yet)",
            recent_messages=recent_text.strip() or "(no recent messages)",
            current_message=current_message,
        )

        client = create_openai_client(
            base_url=settings.rag_openai_api_base_url,
            api_key=settings.rag_openai_api_key,
        )

        parse_kwargs: dict[str, Any] = {
            "model": settings.rag_classification_model,
            "messages": [{"role": "user", "content": classifier_prompt.text}],
            "response_format": RetrievalClassification,
            "max_tokens": 100,
            "temperature": 0.0,
            "name": "chat.classify_needs_retrieval",
            "metadata": {"stage": "chat.classify_needs_retrieval"},
        }
        if classifier_prompt.langfuse_prompt is not None:
            parse_kwargs["langfuse_prompt"] = classifier_prompt.langfuse_prompt
        response = client.chat.completions.parse(**parse_kwargs)

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

    except APIStatusError as exc:
        # Common auth / base-URL mismatch: concise hint without exposing the key
        logger.warning(
            "Classifier API error (status=%s base_url=%s model=%s); "
            "check RAG_OPENAI_API_BASE_URL / RAG_OPENAI_API_KEY. Defaulting to retrieval.",
            exc.status_code,
            settings.rag_openai_api_base_url,
            settings.rag_classification_model,
        )
        return True
    except Exception:
        logger.warning("Classifier failed; defaulting to retrieval", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# Agent function tools (fix #2)
# ---------------------------------------------------------------------------


def _make_retrieve_tool(db: Session, workspace_id: int):
    """Create a retrieve_company_knowledge function tool closed over db/workspace."""

    def retrieve_company_knowledge_fn(
        query: str,
        team_label: str | None = None,
        category_labels_json: str | None = None,
        period_start_month: str | None = None,
        period_end_month: str | None = None,
        source_ids_json: str | None = None,
    ) -> str:
        """Retrieve company knowledge evidence from uploaded Sources.

        Searches indexed source_content chunks via vector search, validates
        against SQL, and returns citation-ready evidence. Use this tool whenever
        you need factual data from uploaded company Sources to answer a question.

        Args:
            query: Natural language query for semantic search.
            team_label: Optional team filter (e.g. "marketing", "product").
            category_labels_json: Optional JSON array string of category labels
                (e.g. '["analytics_metrics", "revenue_sales"]').
            period_start_month: Optional start month "YYYY-MM".
            period_end_month: Optional end month "YYYY-MM".
            source_ids_json: Optional JSON array string of source integer IDs
                (e.g. '[1, 2, 5]').

        Returns:
            JSON string with compact evidence items and metadata.
        """
        scope = _build_source_scope(
            team_label=team_label,
            category_labels_json=category_labels_json,
            period_start_month=period_start_month,
            period_end_month=period_end_month,
            source_ids_json=source_ids_json,
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


def _build_source_scope(
    team_label: str | None = None,
    category_labels_json: str | None = None,
    period_start_month: str | None = None,
    period_end_month: str | None = None,
    source_ids_json: str | None = None,
) -> SourceScope | None:
    """Parse explicit scalar scope params into a SourceScope.

    Returns None when no scope constraints are provided.
    """
    category_labels: list[str] | None = None
    if category_labels_json:
        try:
            parsed = json.loads(category_labels_json)
            if isinstance(parsed, list):
                category_labels = [str(c) for c in parsed]
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid category_labels_json: %s", category_labels_json)

    source_ids: list[int] | None = None
    if source_ids_json:
        try:
            parsed = json.loads(source_ids_json)
            if isinstance(parsed, list):
                source_ids = [int(i) for i in parsed]
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Invalid source_ids_json: %s", source_ids_json)

    has_any = any([team_label, category_labels, period_start_month, period_end_month, source_ids])
    if not has_any:
        return None

    return SourceScope(
        team_label=team_label,
        category_labels=category_labels,
        period_start_month=period_start_month,
        period_end_month=period_end_month,
        source_ids=source_ids,
    )


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
# Main consultant run (async generator for true SSE streaming)
# ---------------------------------------------------------------------------


async def run_consultant_stream(
    db: Session,
    workspace_id: int,
    context: ContextWindow,
    evidence_bundle: EvidenceBundle | None = None,
) -> AsyncGenerator[tuple[ConsultantEvent, ConsultantResult], None]:
    """Run the consultant agent with true streaming and yield (event, result_accumulator) tuples."""
    settings = get_settings()
    current_message = context.current_user_message or ""
    result = ConsultantResult()
    pending_web_citations: list[CitationRecord] = []

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
    if not settings.rag_openai_api_key:
        async for event_tuple in _fallback_run_async(
            current_message=current_message,
            evidence_bundle=evidence_bundle,
            result=result,
        ):
            yield event_tuple
        return

    # --- Use Agents SDK with true streaming ---
    try:
        from agents import Agent, Runner, function_tool
        from agents.extensions.models.litellm_model import LitellmModel
        from agents.mcp import MCPServerStreamableHttp

        model_name = _normalize_litellm_model(
            settings.rag_chat_model,
            settings.rag_openai_api_base_url,
        )
        model = LitellmModel(
            model=model_name,
            base_url=settings.rag_openai_api_base_url,
            api_key=settings.rag_openai_api_key,
        )

        # Build function tools closed over db/workspace
        retrieve_fn = _make_retrieve_tool(db, workspace_id)
        tavily_fn = _make_tavily_tool()

        retrieve_tool = function_tool(
            retrieve_fn,
            name_override="retrieve_company_knowledge",
        )
        tavily_tool = function_tool(
            tavily_fn,
            name_override="tavily_web_search",
        )

        from app.agents.prompt_registry import load_prompt

        system = load_prompt("consultant-system", CONSULTANT_SYSTEM_PROMPT)
        instructions = (
            f"{system.text}\n\n"
            f"You are operating in workspace_id={workspace_id}. "
            f"Whenever you call an MCP tool that requires workspace_id, "
            f"always pass this exact value."
        )

        mcp_server = MCPServerStreamableHttp(
            params={"url": f"{settings.mcp_base_url}/mcp/"},
            name="consultant-mcp",
            cache_tools_list=True,
        )

        async with mcp_server:
            agent = Agent(
                name="CompanyStrategyConsultant",
                instructions=instructions,
                model=model,
                tools=[retrieve_tool, tavily_tool],
                mcp_servers=[mcp_server],
            )

            stream_result = Runner.run_streamed(
                starting_agent=agent,
                input=history,
            )

            # Stream events as they arrive from the model
            accumulated_text = ""
            async for event in stream_result.stream_events():
                if event.type == "raw_response_event":
                    from openai.types.responses import ResponseTextDeltaEvent

                    if isinstance(event.data, ResponseTextDeltaEvent):
                        delta = event.data.delta
                        accumulated_text += delta
                        result.content = accumulated_text
                        yield (
                            ConsultantEvent(type="text_delta", data={"delta": delta}),
                            result,
                        )

                elif event.type == "run_item_stream_event":
                    if event.name == "tool_called":
                        from agents.items import ToolCallItem

                        if isinstance(event.item, ToolCallItem):
                            raw = event.item.raw_item
                            tool_name = _safe_get(raw, "name", "unknown")
                            call_id = _safe_get(raw, "call_id", "")
                            result.tool_calls.append(
                                ToolCallRecord(
                                    tool_name=tool_name,
                                    status="running",
                                    summary=f"Started {tool_name}",
                                    call_id=call_id or None,
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

                    elif event.name == "tool_output":
                        from agents.items import ToolCallOutputItem

                        if isinstance(event.item, ToolCallOutputItem):
                            raw = _safe_get(event.item, "raw_item", None)
                            call_id = _safe_get(raw, "call_id", "") if raw else ""
                            status_val = "ok"
                            output = _safe_get(event.item, "output", None)
                            if isinstance(output, str) and "error" in output.lower():
                                status_val = "error"
                            matched_tc: ToolCallRecord | None = None
                            for tool_call in reversed(result.tool_calls):
                                if tool_call.call_id == (call_id or None):
                                    tool_call.status = "success" if status_val == "ok" else "failed"
                                    tool_call.summary = f"{tool_call.tool_name} completed" if status_val == "ok" else f"{tool_call.tool_name} failed"
                                    matched_tc = tool_call
                                    break
                            # Collect Tavily web citations from agent-invoked tool output
                            if matched_tc and matched_tc.tool_name == "tavily_web_search" and output:
                                _collect_tavily_citations(output, pending_web_citations)
                            # Only status streamed, no args/raw content
                            yield (
                                ConsultantEvent(
                                    type="tool_result",
                                    data={"call_id": call_id, "ok": status_val == "ok"},
                                ),
                                result,
                            )

            # Use final_output as authoritative full text, fallback to accumulated
            full_text = stream_result.final_output or accumulated_text or ""
            result.content = full_text

            # Extract citations from the response
            _extract_citations(
                result=result,
                full_text=full_text,
                evidence_items_map=evidence_items_map,
                evidence_bundle=evidence_bundle,
            )

            # Append agent-invoked Tavily web citations with correct ordinals
            if pending_web_citations:
                start_ordinal = _next_ordinal(result.citations)
                for i, cit in enumerate(pending_web_citations):
                    cit.ordinal = start_ordinal + i
                    result.citations.append(cit)

    except Exception as e:
        logger.exception("Agent run failed, using fallback")
        result.content = ""
        async for event_tuple in _fallback_run_async(
            current_message=current_message,
            evidence_bundle=evidence_bundle,
            result=result,
            error=str(e),
        ):
            yield event_tuple


def _normalize_litellm_model(model_name: str, base_url: str | None) -> str:
    """Normalize model name for LiteLLM provider routing.

    OpenRouter expects the provider prefix in the model name. If the base URL
    points at OpenRouter and the model isn't already prefixed, add it.
    """
    if not base_url:
        return model_name

    lower_base = base_url.lower()
    if "openrouter.ai" in lower_base and not model_name.startswith("openrouter/"):
        return f"openrouter/{model_name}"

    return model_name


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

    current = context.current_user_message or ""

    # The user message is committed to DB before build_context runs, so it may
    # already appear as the last item in recent_messages. Strip it to avoid
    # sending two consecutive user turns (which most LLMs reject).
    recent = list(context.recent_messages)
    if current and recent and recent[-1].get("role") == "user":
        # Normalise whitespace the same way _context_content does before comparing
        normalised_current = current.replace("\n", " ").strip()
        normalised_last = recent[-1].get("content", "").strip()
        if normalised_last == normalised_current:
            recent = recent[:-1]

    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

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


async def _fallback_run_async(
    current_message: str,
    evidence_bundle: EvidenceBundle | None,
    result: ConsultantResult,
    error: str | None = None,
) -> AsyncGenerator[tuple[ConsultantEvent, ConsultantResult], None]:
    """Async wrapper around _fallback_run for the async streaming path."""
    for event_tuple in _fallback_run(
        current_message=current_message,
        evidence_bundle=evidence_bundle,
        result=result,
        error=error,
    ):
        yield event_tuple


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
            call_id=tc.call_id,
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


def _collect_tavily_citations(
    output: str | None,
    pending: list[CitationRecord],
) -> None:
    """Parse Tavily tool output JSON and append web citation records to *pending*.

    Ordinals are set to 0 here; the caller assigns correct ordinals after
    uploaded-source citations are known.
    """
    if not output:
        return
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return

    results = data.get("results", [])
    request_id = data.get("request_id")

    for r in results:
        url = r.get("url", "")
        if not url:
            continue
        pending.append(
            CitationRecord(
                citation_type=CitationType.WEB,
                ordinal=0,  # reassigned after _extract_citations
                url=url,
                title=r.get("title"),
                domain=_extract_domain(url),
                provider="tavily",
                provider_request_id=request_id,
                snippet=r.get("content"),
                relevance_score=r.get("score"),
                citation_status=CitationStatus.AVAILABLE,
                retrieved_at=datetime.utcnow(),
            )
        )


def _extract_domain(url: str) -> str | None:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None
