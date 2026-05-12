"""Company knowledge retrieval interface.

Retrieves citation-ready evidence chunks from ChromaDB, filtered through
SQL-eligible sources (workspace, ProcessingStatus.READY, not soft-deleted,
and optional scope filters).

SQL is the source of truth; ChromaDB vectors are derived.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import Session, select

from app.knowledge.chroma import get_company_knowledge_collection
from app.knowledge.embeddings import get_embeddings_for_texts
from app.models.enums import ArtifactType, ProcessingStatus
from app.models.source import SourceArtifact, SourceCategory, SourceData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SourceScope:
    """Optional filters that narrow the eligible source set."""

    team_label: str | None = None
    category_labels: list[str] | None = None
    period_start_month: str | None = None
    period_end_month: str | None = None
    source_ids: list[int] | None = None


@dataclass
class EvidenceItem:
    """One citation-ready chunk of evidence."""

    citation_id: str
    source_id: int
    artifact_id: int
    chunk_id: str
    source_title: str
    file_type: str
    team_label: str
    category_labels: list[str]
    period_start_month: str | None
    period_end_month: str | None
    quote: str
    page_number: int | None
    row_refs: Any | None
    content_type: str
    document_section: str
    relevance_score: float
    why_relevant: str | None = None


@dataclass
class EvidenceBundle:
    """Result bundle returned to callers (agent tools, chat, etc.)."""

    items: list[EvidenceItem] = field(default_factory=list)
    insufficient_evidence: bool = False
    reason: str | None = None
    candidate_count: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Pattern to collapse whitespace for dedupe comparison
_WHITESPACE_RE = re.compile(r"\s+")


def _normalise_quote(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


# ---------------------------------------------------------------------------
# Eligibility SQL
# ---------------------------------------------------------------------------


def _eligible_source_ids(
    session: Session,
    workspace_id: int,
    scope: SourceScope | None,
) -> list[int]:
    """Return source IDs that pass workspace/Ready/not-deleted + scope filters."""

    base = (
        select(SourceData.id)
        .where(
            SourceData.workspace_id == workspace_id,
            SourceData.processing_status == str(ProcessingStatus.READY),
            SourceData.deleted_at.is_(None),  # type: ignore[union-attr]
        )
    )

    # --- scope filters ---
    if scope is not None:
        if scope.team_label is not None:
            base = base.where(SourceData.team_label == scope.team_label)

        if scope.source_ids is not None:
            base = base.where(SourceData.id.in_(scope.source_ids))

        # Period overlap: source.start <= scope.end AND source.end >= scope.start
        if scope.period_start_month is not None and scope.period_end_month is not None:
            base = base.where(
                SourceData.period_start_month <= scope.period_end_month,
                SourceData.period_end_month >= scope.period_start_month,
            )

        # Category: source must have at least one matching category
        if scope.category_labels:
            cat_source_ids = (
                select(SourceCategory.source_id)
                .where(SourceCategory.category.in_(scope.category_labels))
                .distinct()
            )
            base = base.where(SourceData.id.in_(cat_source_ids))

    rows = session.exec(base).all()
    return list(rows)


# ---------------------------------------------------------------------------
# Main retrieval facade
# ---------------------------------------------------------------------------


def retrieve_company_knowledge(
    session: Session,
    workspace_id: int,
    query: str,
    source_scope: SourceScope | None = None,
    *,
    max_results: int = 10,
    max_chunks_per_source: int = 3,
    min_relevance_score: float = 0.2,
) -> EvidenceBundle:
    """Retrieve citation-ready evidence chunks for *query*.

    1. SQL eligibility filter → eligible source IDs.
    2. Chroma vector search within eligible IDs.
    3. SQL validate / hydrate every candidate.
    4. Dedupe, rerank, per-source diversity cap, quality gate.
    """
    # --- 1. Eligibility ---
    eligible_ids = _eligible_source_ids(session, workspace_id, source_scope)

    if not eligible_ids:
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="No eligible sources found for workspace/scope",
        )

    # --- 2. Chroma search ---
    collection = get_company_knowledge_collection()
    if collection is None:
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="ChromaDB unavailable",
        )

    query_embedding = get_embeddings_for_texts([query])[0]

    # Build Chroma where filter for eligible source IDs
    if len(eligible_ids) == 1:
        chroma_where: dict[str, Any] = {"source_id": eligible_ids[0]}
    else:
        chroma_where = {"source_id": {"$in": eligible_ids}}

    try:
        chroma_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max_results * 3, 50),  # fetch extra for post-filtering
            where=chroma_where,
            include=["metadatas", "distances"],
        )
    except Exception:
        logger.warning("ChromaDB query failed", exc_info=True)
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="ChromaDB query error",
        )

    # Unpack Chroma result lists (single query ⇒ first element of each)
    chroma_ids_list: list[str] = (chroma_results.get("ids") or [[]])[0]
    chroma_metas: list[dict] = (chroma_results.get("metadatas") or [[]])[0]
    chroma_dists: list[float | None] = (chroma_results.get("distances") or [[]])[0]

    if not chroma_ids_list:
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="No vector candidates returned",
            candidate_count=0,
        )

    # --- 3. Validate / hydrate via SQL ---
    # Pre-load valid source IDs for fast lookup
    valid_sources = session.exec(
        select(SourceData).where(
            SourceData.id.in_(eligible_ids),
            SourceData.processing_status == str(ProcessingStatus.READY),
            SourceData.deleted_at.is_(None),  # type: ignore[union-attr]
        )
    ).all()
    source_map: dict[int, SourceData] = {s.id: s for s in valid_sources}

    # Pre-load source_content artifacts for eligible sources
    artifacts = session.exec(
        select(SourceArtifact).where(
            SourceArtifact.source_id.in_(eligible_ids),
            SourceArtifact.artifact_type == str(ArtifactType.SOURCE_CONTENT),
        )
    ).all()
    artifact_map: dict[int, SourceArtifact] = {a.id: a for a in artifacts}

    # Build chunk lookup: artifact_id -> set of chunk_id values
    chunk_lookup: dict[int, dict[str, dict]] = {}
    for art in artifacts:
        content_json = art.content_json or {}
        chunks = content_json.get("chunks", [])
        chunk_lookup[art.id] = {c.get("chunk_id", str(c.get("chunk_index", ""))): c for c in chunks}

    # Pre-load categories per source
    all_categories = session.exec(
        select(SourceCategory).where(SourceCategory.source_id.in_(eligible_ids))
    ).all()
    cat_map: dict[int, list[str]] = {}
    for cat in all_categories:
        cat_map.setdefault(cat.source_id, []).append(str(cat.category))

    # Validate each candidate
    raw_items: list[EvidenceItem] = []
    seen_ids: set[str] = set()

    for idx, vector_id in enumerate(chroma_ids_list):
        meta = chroma_metas[idx] if idx < len(chroma_metas) else {}
        dist = chroma_dists[idx] if idx < len(chroma_dists) else None

        src_id = meta.get("source_id")
        art_id = meta.get("artifact_id")
        chunk_id = meta.get("chunk_id", "")

        # Validate source
        if src_id is None or src_id not in source_map:
            continue
        source = source_map[int(src_id)]

        # Validate artifact
        if art_id is None or art_id not in artifact_map:
            continue
        art = artifact_map[art_id]
        if art.source_id != src_id:
            continue

        # Validate chunk exists in artifact content_json
        art_chunks = chunk_lookup.get(art_id, {})
        canonical_chunk = art_chunks.get(chunk_id)
        if canonical_chunk is None:
            # Try chunk_index fallback
            chunk_idx = meta.get("chunk_index")
            alt_key = str(chunk_idx) if chunk_idx is not None else None
            if alt_key is None or alt_key not in art_chunks:
                continue
            canonical_chunk = art_chunks[alt_key]

        canonical_chunk_id = str(canonical_chunk.get("chunk_id", canonical_chunk.get("chunk_index", chunk_id)))
        quote = str(canonical_chunk.get("text", "")).strip()
        if not quote:
            continue

        # Dedupe by vector_id
        if vector_id in seen_ids:
            continue
        seen_ids.add(vector_id)

        # Compute relevance score
        if dist is not None:
            relevance = max(0.0, min(1.0, 1.0 - dist))
        else:
            relevance = 1.0

        item = EvidenceItem(
            citation_id=vector_id,
            source_id=int(src_id),
            artifact_id=int(art_id),
            chunk_id=canonical_chunk_id,
            source_title=source.title,
            file_type=str(source.file_type),
            team_label=str(source.team_label),
            category_labels=cat_map.get(int(src_id), []),
            period_start_month=source.period_start_month,
            period_end_month=source.period_end_month,
            quote=quote,
            page_number=canonical_chunk.get("page_number"),
            row_refs=canonical_chunk.get("row_refs") or canonical_chunk.get("row_count"),
            content_type=str(canonical_chunk.get("content_type", "")),
            document_section=str(canonical_chunk.get("document_section", "")),
            relevance_score=relevance,
        )
        raw_items.append(item)

    candidate_count = len(raw_items)

    if not raw_items:
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="No valid candidates after SQL validation",
            candidate_count=candidate_count,
        )

    # --- 4. Dedupe near-identical chunks ---
    deduped: list[EvidenceItem] = []
    seen_quotes: set[str] = set()
    for item in raw_items:
        key = _normalise_quote(item.quote)
        if key not in seen_quotes:
            seen_quotes.add(key)
            deduped.append(item)

    # --- 5. Rerank by relevance_score descending ---
    deduped.sort(key=lambda i: i.relevance_score, reverse=True)

    # --- 6. Per-source diversity cap ---
    capped: list[EvidenceItem] = []
    per_source_counts: dict[int, int] = {}
    for item in deduped:
        count = per_source_counts.get(item.source_id, 0)
        if count >= max_chunks_per_source:
            continue
        per_source_counts[item.source_id] = count + 1
        capped.append(item)
        if len(capped) >= max_results:
            break

    # --- 7. Quality gate ---
    if not capped or capped[0].relevance_score < min_relevance_score:
        reason = "No items after diversity cap"
        if capped:
            reason = f"Top relevance {capped[0].relevance_score:.3f} below threshold {min_relevance_score}"
        return EvidenceBundle(
            insufficient_evidence=True,
            reason=reason,
            candidate_count=candidate_count,
        )

    return EvidenceBundle(
        items=capped,
        candidate_count=candidate_count,
    )
