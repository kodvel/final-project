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
from app.models.decision_brief import DecisionBrief
from app.models.enums import ArtifactType, DecisionApprovalStatus, ProcessingStatus
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
    source_id: int | None
    artifact_id: int | None
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
    source_kind: str = "uploaded_source"
    decision_brief_id: int | None = None


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


def _document_for_vector(chroma_results: dict, idx: int) -> str:
    docs = (chroma_results.get("documents") or [[]])[0]
    if idx >= len(docs):
        return ""
    text = docs[idx]
    return str(text).strip() if text else ""


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


def _eligible_decision_brief_ids(
    session: Session,
    workspace_id: int,
    scope: SourceScope | None,
) -> list[int]:
    """Return approved Decision Brief IDs for the workspace.

    Approved briefs become cross-session knowledge. Explicit source_ids scope
    suppresses brief retrieval — the user is constraining to specific sources.
    """
    if scope is not None and scope.source_ids:
        return []
    rows = session.exec(
        select(DecisionBrief.id).where(
            DecisionBrief.workspace_id == workspace_id,
            DecisionBrief.approval_status == DecisionApprovalStatus.APPROVED,
        )
    ).all()
    return list(rows)


def _build_chroma_where(
    eligible_source_ids: list[int],
    approved_brief_ids: list[int],
    workspace_id: int,
) -> dict[str, Any]:
    """Compose a Chroma ``where`` filter that matches eligible uploaded sources
    and approved Decision Briefs, scoped by workspace.
    """
    clauses: list[dict[str, Any]] = []
    if eligible_source_ids:
        if len(eligible_source_ids) == 1:
            clauses.append({"source_id": eligible_source_ids[0]})
        else:
            clauses.append({"source_id": {"$in": eligible_source_ids}})
    if approved_brief_ids:
        if len(approved_brief_ids) == 1:
            brief_clause: dict[str, Any] = {"decision_brief_id": approved_brief_ids[0]}
        else:
            brief_clause = {"decision_brief_id": {"$in": approved_brief_ids}}
        clauses.append({
            "$and": [
                {"workspace_id": workspace_id},
                {"source_kind": "decision_brief"},
                brief_clause,
            ]
        })
    if len(clauses) == 1:
        return clauses[0]
    return {"$or": clauses}


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
    approved_brief_ids = _eligible_decision_brief_ids(session, workspace_id, source_scope)

    if not eligible_ids and not approved_brief_ids:
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="No eligible sources or approved Decision Briefs found for workspace/scope",
        )

    # --- 2. Chroma search ---
    collection = get_company_knowledge_collection()
    if collection is None:
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="ChromaDB unavailable",
        )

    # Build Chroma where filter: uploaded source chunks OR approved decision briefs
    chroma_where = _build_chroma_where(eligible_ids, approved_brief_ids, workspace_id)

    # Clamp n_results by collection size — the Rust-backed Chroma backend
    # errors out (rather than returning fewer results) when n_results exceeds
    # the available document count. This hits brand-new workspaces hardest
    # because they may only have a handful of chunks indexed.
    try:
        collection_count = collection.count()
    except Exception:
        collection_count = 0
    if collection_count == 0:
        return EvidenceBundle(
            insufficient_evidence=True,
            reason="ChromaDB collection is empty",
        )
    requested = min(max_results * 3, 50, collection_count)

    chroma_results = None
    last_error: Exception | None = None
    # Chroma 1.x Rust-backend can raise transient "Error finding id" right
    # after a write commits to the WAL but before the HNSW index ingests it.
    # Retry with backoff — usually resolves within 1–2s as compaction catches up.
    import time as _time

    backoff_seconds = (0.0, 0.5, 1.5, 3.0)
    for attempt, delay in enumerate(backoff_seconds):
        if delay > 0:
            _time.sleep(delay)
        try:
            chroma_results = collection.query(
                query_texts=[query],
                n_results=requested,
                where=chroma_where,
                include=["metadatas", "distances", "documents"],
            )
            break
        except Exception as exc:
            last_error = exc
            logger.warning(
                "ChromaDB query failed (attempt %d/%d, n_results=%d): %s",
                attempt + 1,
                len(backoff_seconds),
                requested,
                exc,
            )

    if chroma_results is None:
        logger.error("ChromaDB query exhausted retries; giving up", exc_info=last_error)
        return EvidenceBundle(
            insufficient_evidence=True,
            reason=f"ChromaDB query error: {last_error}",
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
    ).all() if eligible_ids else []
    source_map: dict[int, SourceData] = {s.id: s for s in valid_sources}

    # Pre-load source_content artifacts for eligible sources
    artifacts = session.exec(
        select(SourceArtifact).where(
            SourceArtifact.source_id.in_(eligible_ids),
            SourceArtifact.artifact_type == str(ArtifactType.SOURCE_CONTENT),
        )
    ).all() if eligible_ids else []
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
    ).all() if eligible_ids else []
    cat_map: dict[int, list[str]] = {}
    for cat in all_categories:
        cat_map.setdefault(cat.source_id, []).append(str(cat.category))

    # Pre-load approved decision briefs for hydration
    brief_map: dict[int, DecisionBrief] = {}
    if approved_brief_ids:
        approved_briefs = session.exec(
            select(DecisionBrief).where(
                DecisionBrief.id.in_(approved_brief_ids),
                DecisionBrief.approval_status == DecisionApprovalStatus.APPROVED,
            )
        ).all()
        brief_map = {b.id: b for b in approved_briefs}

    # Validate each candidate
    raw_items: list[EvidenceItem] = []
    seen_ids: set[str] = set()

    for idx, vector_id in enumerate(chroma_ids_list):
        meta = chroma_metas[idx] if idx < len(chroma_metas) else {}
        dist = chroma_dists[idx] if idx < len(chroma_dists) else None

        # Dedupe by vector_id
        if vector_id in seen_ids:
            continue

        # Compute relevance score
        if dist is not None:
            relevance = max(0.0, min(1.0, 1.0 - dist))
        else:
            relevance = 1.0

        if meta.get("source_kind") == "decision_brief":
            brief_id = meta.get("decision_brief_id")
            if brief_id is None or int(brief_id) not in brief_map:
                continue
            brief = brief_map[int(brief_id)]
            quote = _document_for_vector(chroma_results, idx)
            if not quote:
                continue
            seen_ids.add(vector_id)
            raw_items.append(EvidenceItem(
                citation_id=vector_id,
                source_id=None,
                artifact_id=None,
                chunk_id=str(meta.get("document_section") or "section"),
                source_title=str(meta.get("source_title") or brief.title),
                file_type="decision_brief",
                team_label="",
                category_labels=[],
                period_start_month=None,
                period_end_month=None,
                quote=quote,
                page_number=None,
                row_refs=None,
                content_type="decision_brief",
                document_section=str(meta.get("document_section", "")),
                relevance_score=relevance,
                source_kind="decision_brief",
                decision_brief_id=int(brief_id),
            ))
            continue

        # Uploaded source path
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

        seen_ids.add(vector_id)

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
