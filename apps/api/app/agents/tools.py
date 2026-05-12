"""Agent tools for source retrieval, web search, and evidence handling."""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session

from app.knowledge.retrieval import (
    EvidenceBundle,
    SourceScope,
    retrieve_company_knowledge,
)

logger = logging.getLogger(__name__)


def retrieve_knowledge(
    session: Session,
    workspace_id: int,
    query: str,
    source_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retrieve company knowledge evidence from uploaded Sources.

    Searches indexed source_content chunks via ChromaDB, validates against SQL,
    and returns citation-ready evidence. Use this tool whenever you need factual
    data from uploaded company Sources to answer a question.

    Args:
        session: Database session.
        workspace_id: Workspace to scope the search.
        query: Natural language query for semantic search.
        source_scope: Optional scope filters (team_label, category_labels,
            period_start_month, period_end_month, source_ids).

    Returns:
        Serialized EvidenceBundle with items and metadata.
    """
    scope = _parse_scope(source_scope) if source_scope else None
    bundle = retrieve_company_knowledge(session, workspace_id, query, scope)
    return _serialize_bundle(bundle)


def tavily_web_search(
    query: str,
    max_results: int = 5,
) -> dict[str, Any]:
    """Search the web using Tavily for public, current, web-answerable information.

    IMPORTANT RESTRICTIONS:
    - Use ONLY when uploaded Source evidence is weak or empty.
    - Use ONLY for questions about public market data, industry trends, competitor
      public information, or generally available web knowledge.
    - NEVER use to replace uploaded Sources for internal company facts.
    - NEVER use for source-specific internal questions (team metrics, product data,
      customer insights that should come from uploaded Sources).
    - Web evidence must be clearly labeled as "Web Source" in your response.

    Args:
        query: Search query for public/web information.
        max_results: Maximum number of results (default 5).

    Returns:
        Dictionary with search results including title, url, content, score.
    """
    from app.core.config import get_settings

    settings = get_settings()
    api_key = settings.tavily_api_key

    if not api_key:
        return {
            "results": [],
            "error": "Tavily API key not configured",
            "query": query,
        }

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
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
                "published_date": r.get("published_date"),
            })

        return {
            "results": results,
            "query": query,
            "request_id": response.get("request_id"),
        }
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return {
            "results": [],
            "error": f"Web search failed: {e}",
            "query": query,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def retrieve_company_knowledge_tool(
    session: Session,
    workspace_id: int,
    query: str,
    source_scope: SourceScope | None = None,
) -> EvidenceBundle:
    """Agent-callable wrapper around :func:`retrieve_company_knowledge`.

    Returns an :class:`EvidenceBundle` the agent can use to ground its
    response with source citations.
    """
    return retrieve_company_knowledge(
        session,
        workspace_id,
        query,
        source_scope=source_scope,
    )


def _parse_scope(scope_dict: dict[str, Any]) -> SourceScope:
    """Convert a dict to a SourceScope."""
    return SourceScope(
        team_label=scope_dict.get("team_label"),
        category_labels=scope_dict.get("category_labels"),
        period_start_month=scope_dict.get("period_start_month"),
        period_end_month=scope_dict.get("period_end_month"),
        source_ids=scope_dict.get("source_ids"),
    )


def _serialize_bundle(bundle: EvidenceBundle) -> dict[str, Any]:
    """Convert EvidenceBundle to a JSON-serializable dict."""
    items = []
    for item in bundle.items:
        items.append({
            "citation_id": item.citation_id,
            "source_id": item.source_id,
            "artifact_id": item.artifact_id,
            "chunk_id": item.chunk_id,
            "source_title": item.source_title,
            "file_type": item.file_type,
            "team_label": item.team_label,
            "category_labels": item.category_labels,
            "period_start_month": item.period_start_month,
            "period_end_month": item.period_end_month,
            "quote": item.quote,
            "page_number": item.page_number,
            "row_refs": item.row_refs,
            "content_type": item.content_type,
            "document_section": item.document_section,
            "relevance_score": item.relevance_score,
            "why_relevant": item.why_relevant,
        })
    return {
        "items": items,
        "insufficient_evidence": bundle.insufficient_evidence,
        "reason": bundle.reason,
        "candidate_count": bundle.candidate_count,
    }
