"""Index source_content chunks into ChromaDB for retrieval.

SQL remains the source of truth.  ChromaDB vectors are derived and fully
rebuildable from ``source_content`` artifacts.
"""

from __future__ import annotations

import json
import logging

from sqlmodel import Session, select

from app.knowledge.chroma import get_company_knowledge_collection
from app.models.enums import ArtifactType
from app.models.source import SourceArtifact, SourceCategory, SourceData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def index_source_content(session: Session, source_id: int) -> int:
    """Index all ``source_content`` chunks for *source_id* into ChromaDB.

    Returns the number of chunks upserted.
    """
    source = session.get(SourceData, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")

    # Load the source_content artifact
    artifact = session.exec(
        select(SourceArtifact).where(
            SourceArtifact.source_id == source_id,
            SourceArtifact.artifact_type == str(ArtifactType.SOURCE_CONTENT),
        )
    ).first()
    if artifact is None:
        raise ValueError(f"No source_content artifact for source {source_id}")

    content_json = artifact.content_json
    chunks = content_json.get("chunks", [])
    if not chunks:
        logger.warning("source_content artifact %s has no chunks; skipping indexing", artifact.id)
        return 0

    # Load category labels
    categories = session.exec(
        select(SourceCategory.category).where(SourceCategory.source_id == source_id)
    ).all()
    category_labels = [str(c) for c in categories]

    collection = get_company_knowledge_collection()
    if collection is None:
        logger.warning("ChromaDB unavailable; skipping indexing for source %s", source_id)
        return 0

    # Build vectors
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for chunk in chunks:
        chunk_text = chunk.get("text", "")
        if not chunk_text or not chunk_text.strip():
            continue

        chunk_index = chunk.get("chunk_index", 0)
        vector_id = f"source:{source_id}:artifact:{artifact.id}:chunk:{chunk_index}"
        ids.append(vector_id)
        documents.append(chunk_text)

        meta: dict = {
            "workspace_id": source.workspace_id,
            "source_id": source_id,
            "artifact_id": artifact.id,
            "chunk_id": chunk.get("chunk_id", str(chunk_index)),
            "source_title": source.title,
            "file_type": str(source.file_type),
            "team_label": str(source.team_label),
            "category_labels": json.dumps(category_labels),
            "period_start_month": source.period_start_month,
            "period_end_month": source.period_end_month,
            "content_type": str(chunk.get("content_type", "")),
            "document_section": str(chunk.get("document_section", "")),
            "chunk_index": chunk_index,
            "created_at": source.created_at.isoformat() if source.created_at else "",
        }
        # Optional fields — PDF-specific
        page_number = chunk.get("page_number")
        if page_number is not None:
            meta["page_number"] = int(page_number)

        # Optional fields — CSV-specific
        columns = chunk.get("columns")
        if columns:
            meta["columns"] = json.dumps(columns) if isinstance(columns, list) else str(columns)

        row_refs = chunk.get("row_refs") or chunk.get("row_count")
        if row_refs is not None:
            meta["row_refs"] = str(row_refs)

        metadatas.append(meta)

    if not ids:
        return 0

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Indexed %d chunks for source %s", len(ids), source_id)
    return len(ids)


def delete_source_vectors(source_id: int) -> None:
    """Delete all ChromaDB vectors for *source_id* (best-effort)."""
    collection = get_company_knowledge_collection()
    if collection is None:
        return

    try:
        collection.delete(where={"source_id": source_id})
        logger.info("Deleted vectors for source %s", source_id)
    except Exception:
        logger.warning("Failed to delete vectors for source %s; continuing", source_id, exc_info=True)


def reindex_source_content(session: Session, source_id: int) -> int:
    """Delete existing vectors then re-index from SQL source of truth."""
    delete_source_vectors(source_id)
    return index_source_content(session, source_id)


# ---------------------------------------------------------------------------
# Approved Decision Brief indexing
# ---------------------------------------------------------------------------


# Section keys from DecisionBriefContent.content_json that carry textual content
# worth surfacing in retrieval. List values are joined into one document.
_BRIEF_SECTIONS: tuple[str, ...] = (
    "objective",
    "context_problem",
    "strategic_interpretation",
    "recommendation",
    "risks_assumptions",
    "next_steps",
)


def _brief_section_text(value) -> str:
    if isinstance(value, list):
        return "\n".join(str(v).strip() for v in value if str(v).strip())
    if isinstance(value, str):
        return value.strip()
    return ""


def index_decision_brief(brief) -> int:
    """Index an approved Decision Brief's content into the company_knowledge collection.

    Each populated section becomes one Chroma document with metadata that
    flags ``source_kind="decision_brief"`` so retrieval can recognise it as a
    non-source-file knowledge item.
    """
    collection = get_company_knowledge_collection()
    if collection is None:
        logger.warning("ChromaDB unavailable; skipping decision brief %s indexing", brief.id)
        return 0

    content_json = brief.content_json or {}
    title = brief.title or f"Decision Brief #{brief.sequence_number}"
    source_title = f"Decision Brief #{brief.sequence_number} — {title}"

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for section in _BRIEF_SECTIONS:
        text = _brief_section_text(content_json.get(section))
        if not text:
            continue
        document = f"{title}\n\n{section.replace('_', ' ').title()}:\n{text}"
        ids.append(f"decision_brief:{brief.id}:{section}")
        documents.append(document)
        metadatas.append({
            "workspace_id": brief.workspace_id,
            "decision_brief_id": brief.id,
            "sequence_number": brief.sequence_number,
            "recommendation_status": str(brief.recommendation_status),
            "approval_status": "approved",
            "source_kind": "decision_brief",
            "source_title": source_title,
            "document_section": section,
            "content_type": "decision_brief",
            "created_at": brief.created_at.isoformat() if brief.created_at else "",
        })

    if not ids:
        logger.info("Decision brief %s has no indexable sections", brief.id)
        return 0

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Indexed %d sections for decision brief %s", len(ids), brief.id)
    return len(ids)


def delete_decision_brief_vectors(brief_id: int) -> None:
    """Delete all ChromaDB vectors for a Decision Brief (best-effort)."""
    collection = get_company_knowledge_collection()
    if collection is None:
        return
    try:
        collection.delete(where={"decision_brief_id": brief_id})
        logger.info("Deleted vectors for decision brief %s", brief_id)
    except Exception:
        logger.warning(
            "Failed to delete vectors for decision brief %s; continuing",
            brief_id,
            exc_info=True,
        )
