"""Agent tools for source retrieval, CSV artifacts, and Decision Briefs."""

from __future__ import annotations

from sqlmodel import Session

from app.knowledge.retrieval import (
    EvidenceBundle,
    SourceScope,
    retrieve_company_knowledge,
)


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
