"""Tests for company knowledge retrieval (Task 4 acceptance criteria)."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models.enums import (
    ArtifactType,
    ProcessingStatus,
    SourceFileType,
    TeamLabel,
)
from app.models.source import SourceArtifact, SourceCategory, SourceData

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session(tmp_path):
    """Isolated in-memory session for unit tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _make_source(session: Session, **overrides) -> SourceData:
    defaults = dict(
        workspace_id=1,
        title="Test Source",
        team_label=TeamLabel.MARKETING,
        file_type=SourceFileType.CSV,
        original_filename="data.csv",
        storage_path="/tmp/data.csv",
        period_start_month="2026-01",
        period_end_month="2026-03",
        processing_status=ProcessingStatus.READY,
    )
    defaults.update(overrides)
    source = SourceData(**defaults)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def _make_categories(session: Session, source_id: int, labels: list[str]) -> None:
    for label in labels:
        session.add(SourceCategory(source_id=source_id, category=label))
    session.commit()


def _make_content_artifact(
    session: Session, source_id: int, chunks: list[dict], **overrides
) -> SourceArtifact:
    defaults = dict(
        source_id=source_id,
        artifact_type=str(ArtifactType.SOURCE_CONTENT),
        title="Content: Test",
        content_json={"chunks": chunks, "summary": "test", "statistics": {}},
    )
    defaults.update(overrides)
    artifact = SourceArtifact(**defaults)
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return artifact


def _chroma_result(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
    distances: list[float],
) -> dict:
    """Build a Chroma query result dict for a single query."""
    return {
        "ids": [ids],
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }


# ---------------------------------------------------------------------------
# 1. Returns source references and citation-ready evidence
# ---------------------------------------------------------------------------


def test_retrieval_returns_citation_ready_evidence(session):
    """Happy path: returns EvidenceBundle with citation-ready items."""
    source = _make_source(session, title="Revenue Report")
    _make_categories(session, source.id, ["analytics_metrics"])
    chunks = [
        {
            "chunk_id": "c-0",
            "text": "Revenue grew 15% in Q1 2026",
            "content_type": "metric",
            "document_section": "financials",
            "chunk_index": 0,
        },
    ]
    artifact = _make_content_artifact(session, source.id, chunks)

    meta = {
        "source_id": source.id,
        "artifact_id": artifact.id,
        "chunk_id": "c-0",
        "source_title": "Revenue Report",
        "file_type": "csv",
        "team_label": "marketing",
        "category_labels": json.dumps(["analytics_metrics"]),
        "period_start_month": "2026-01",
        "period_end_month": "2026-03",
        "content_type": "metric",
        "document_section": "financials",
        "chunk_index": 0,
    }

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[f"source:{source.id}:artifact:{artifact.id}:chunk:0"],
        documents=["Revenue grew 15% in Q1 2026"],
        metadatas=[meta],
        distances=[0.15],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="revenue growth")

    assert not bundle.insufficient_evidence
    assert len(bundle.items) == 1
    item = bundle.items[0]
    assert item.source_id == source.id
    assert item.artifact_id == artifact.id
    assert item.chunk_id == "c-0"
    assert item.source_title == "Revenue Report"
    assert item.quote == "Revenue grew 15% in Q1 2026"
    assert item.category_labels == ["analytics_metrics"]
    assert item.relevance_score == pytest.approx(0.85)  # 1 - 0.15


def test_retrieval_uses_query_texts_not_embeddings(session):
    """Retrieval calls collection.query with query_texts, not query_embeddings."""
    source = _make_source(session, title="Query Test")
    _make_content_artifact(session, source.id, [{"chunk_id": "c-0", "text": "test", "chunk_index": 0}])

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[], documents=[], metadatas=[], distances=[],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        retrieve_company_knowledge(session, workspace_id=1, query="test query")

    call_kwargs = fake_collection.query.call_args[1]
    # Should use query_texts for Chroma auto-embedding
    assert call_kwargs.get("query_texts") == ["test query"]
    # Should NOT include query_embeddings
    assert "query_embeddings" not in call_kwargs


def test_retrieval_hydrates_evidence_from_sql_not_chroma_payload(session):
    """Chroma proposes candidates; SQL Source Artifact supplies canonical evidence."""
    source = _make_source(
        session,
        title="Canonical SQL Source",
        file_type=SourceFileType.PDF,
        team_label=TeamLabel.PRODUCT,
        period_start_month="2026-04",
        period_end_month="2026-06",
    )
    _make_categories(session, source.id, ["product_feature"])
    chunks = [
        {
            "chunk_id": "canonical-c-0",
            "text": "Canonical SQL quote with page ref",
            "content_type": "quote",
            "document_section": "product_feature",
            "chunk_index": 0,
            "page_number": 7,
            "row_refs": {"rows": [2, 3]},
        },
    ]
    artifact = _make_content_artifact(session, source.id, chunks)

    stale_meta = {
        "source_id": source.id,
        "artifact_id": artifact.id,
        "chunk_id": "canonical-c-0",
        "source_title": "Stale Chroma Title",
        "file_type": "csv",
        "team_label": "marketing",
        "period_start_month": "2025-01",
        "period_end_month": "2025-01",
        "content_type": "metric",
        "document_section": "financials",
        "chunk_index": 0,
        "page_number": 99,
        "row_refs": "stale rows",
    }

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[f"source:{source.id}:artifact:{artifact.id}:chunk:0"],
        documents=["Stale Chroma quote"],
        metadatas=[stale_meta],
        distances=[0.1],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="product quote")

    assert not bundle.insufficient_evidence
    item = bundle.items[0]
    assert item.source_title == "Canonical SQL Source"
    assert item.file_type == "pdf"
    assert item.team_label == "product"
    assert item.period_start_month == "2026-04"
    assert item.period_end_month == "2026-06"
    assert item.quote == "Canonical SQL quote with page ref"
    assert item.page_number == 7
    assert item.row_refs == {"rows": [2, 3]}
    assert item.content_type == "quote"
    assert item.document_section == "product_feature"


# ---------------------------------------------------------------------------
# 2. Validates workspace/Ready/deleted/artifact existence; discards invalid
# ---------------------------------------------------------------------------


def test_discards_candidates_from_wrong_workspace(session):
    """Candidates from a different workspace are discarded."""
    # Source in workspace 1
    source_ws1 = _make_source(session, workspace_id=1, title="WS1 Source")
    chunks_ws1 = [{"chunk_id": "c-0", "text": "WS1 data", "chunk_index": 0}]
    _make_content_artifact(session, source_ws1.id, chunks_ws1)

    # Source in workspace 2
    source_ws2 = _make_source(session, workspace_id=2, title="WS2 Source")
    chunks_ws2 = [{"chunk_id": "c-0", "text": "WS2 data", "chunk_index": 0}]
    art_ws2 = _make_content_artifact(session, source_ws2.id, chunks_ws2)

    # Chroma returns the WS2 candidate
    meta_ws2 = {
        "source_id": source_ws2.id,
        "artifact_id": art_ws2.id,
        "chunk_id": "c-0",
        "source_title": "WS2 Source",
        "file_type": "csv",
        "team_label": "marketing",
        "category_labels": "[]",
        "period_start_month": "2026-01",
        "period_end_month": "2026-03",
        "content_type": "",
        "document_section": "",
        "chunk_index": 0,
    }

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[f"source:{source_ws2.id}:artifact:{art_ws2.id}:chunk:0"],
        documents=["WS2 data"],
        metadatas=[meta_ws2],
        distances=[0.1],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="data")

    # WS2 source not in eligible IDs for workspace 1 → Chroma filtered it out
    # But even if Chroma returned it, SQL validation would discard it
    assert bundle.insufficient_evidence


def test_discards_soft_deleted_source(session):
    """Soft-deleted sources are not eligible."""
    source = _make_source(session, title="Deleted Source")
    source.deleted_at = datetime.utcnow()
    session.add(source)
    session.commit()

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=MagicMock()):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="deleted")

    assert bundle.insufficient_evidence
    assert "No eligible sources" in (bundle.reason or "")


def test_discards_non_ready_source(session):
    """Sources with status != READY are not eligible."""
    _make_source(session, processing_status=ProcessingStatus.PROCESSING)

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=MagicMock()):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="processing")

    assert bundle.insufficient_evidence


def test_discards_candidates_with_missing_artifact(session):
    """Candidates whose artifact_id doesn't exist are discarded."""
    source = _make_source(session, title="No Artifact Source")
    # No artifact created for this source
    meta = {
        "source_id": source.id,
        "artifact_id": 99999,  # non-existent
        "chunk_id": "c-0",
        "source_title": "No Artifact Source",
        "file_type": "csv",
        "team_label": "marketing",
        "category_labels": "[]",
        "period_start_month": "2026-01",
        "period_end_month": "2026-03",
        "content_type": "",
        "document_section": "",
        "chunk_index": 0,
    }

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=["fake:vec:0"],
        documents=["orphan chunk"],
        metadatas=[meta],
        distances=[0.1],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="orphan")

    assert bundle.insufficient_evidence
    assert "No valid candidates" in (bundle.reason or "")


def test_discards_candidates_with_chunk_not_in_artifact(session):
    """Candidates whose chunk_id doesn't exist in artifact.content_json.chunks are discarded."""
    source = _make_source(session, title="Mismatched Chunk")
    chunks = [{"chunk_id": "c-0", "text": "actual chunk", "chunk_index": 0}]
    artifact = _make_content_artifact(session, source.id, chunks)

    # Chroma returns a chunk_id that doesn't exist in artifact
    meta = {
        "source_id": source.id,
        "artifact_id": artifact.id,
        "chunk_id": "c-nonexistent",
        "source_title": "Mismatched Chunk",
        "file_type": "csv",
        "team_label": "marketing",
        "category_labels": "[]",
        "period_start_month": "2026-01",
        "period_end_month": "2026-03",
        "content_type": "",
        "document_section": "",
        "chunk_index": 99,
    }

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=["fake:vec:99"],
        documents=["phantom chunk"],
        metadatas=[meta],
        distances=[0.1],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="phantom")

    assert bundle.insufficient_evidence
    assert "No valid candidates" in (bundle.reason or "")


# ---------------------------------------------------------------------------
# 3. Scope filters affect eligible source IDs passed to Chroma
# ---------------------------------------------------------------------------


def test_scope_filters_by_team_label(session):
    """Scope team_label restricts eligible sources."""
    mk_source = _make_source(session, team_label=TeamLabel.MARKETING, title="Marketing Source")
    _make_source(session, team_label=TeamLabel.PRODUCT, title="Product Source")

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[], documents=[], metadatas=[], distances=[],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import SourceScope, retrieve_company_knowledge

        retrieve_company_knowledge(
            session,
            workspace_id=1,
            query="test",
            source_scope=SourceScope(team_label="marketing"),
        )

    # Chroma where should filter to only marketing source
    call_kwargs = fake_collection.query.call_args[1]
    chroma_where = call_kwargs["where"]
    assert chroma_where == {"source_id": mk_source.id}


def test_scope_filters_by_category(session):
    """Scope category_labels restricts eligible sources via SourceCategory."""
    s1 = _make_source(session, title="Analytics Source")
    _make_categories(session, s1.id, ["analytics_metrics"])

    s2 = _make_source(session, title="Competitor Source")
    _make_categories(session, s2.id, ["competitor_analysis"])

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[], documents=[], metadatas=[], distances=[],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import SourceScope, retrieve_company_knowledge

        retrieve_company_knowledge(
            session,
            workspace_id=1,
            query="test",
            source_scope=SourceScope(category_labels=["analytics_metrics"]),
        )

    call_kwargs = fake_collection.query.call_args[1]
    chroma_where = call_kwargs["where"]
    # Should only contain s1's id
    if "$in" in str(chroma_where):
        assert s1.id in chroma_where["source_id"]["$in"]
        assert s2.id not in chroma_where["source_id"]["$in"]
    else:
        assert chroma_where["source_id"] == s1.id


def test_scope_filters_by_period_overlap(session):
    """Scope period overlap excludes non-overlapping sources."""
    # Source covers Jan-Mar 2026
    _make_source(
        session,
        title="Q1 Source",
        period_start_month="2026-01",
        period_end_month="2026-03",
    )
    # Source covers Jul-Sep 2026
    s_q3 = _make_source(
        session,
        title="Q3 Source",
        period_start_month="2026-07",
        period_end_month="2026-09",
    )

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[], documents=[], metadatas=[], distances=[],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import SourceScope, retrieve_company_knowledge

        # Scope asks for Jul-Aug 2026 → only Q3 source eligible
        retrieve_company_knowledge(
            session,
            workspace_id=1,
            query="test",
            source_scope=SourceScope(
                period_start_month="2026-07",
                period_end_month="2026-08",
            ),
        )

    call_kwargs = fake_collection.query.call_args[1]
    chroma_where = call_kwargs["where"]
    assert chroma_where == {"source_id": s_q3.id}


def test_scope_filters_by_source_ids(session):
    """Scope source_ids restricts to specific sources."""
    s1 = _make_source(session, title="Source A")
    s2 = _make_source(session, title="Source B")
    s3 = _make_source(session, title="Source C")

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[], documents=[], metadatas=[], distances=[],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import SourceScope, retrieve_company_knowledge

        retrieve_company_knowledge(
            session,
            workspace_id=1,
            query="test",
            source_scope=SourceScope(source_ids=[s1.id, s3.id]),
        )

    call_kwargs = fake_collection.query.call_args[1]
    chroma_where = call_kwargs["where"]
    eligible = chroma_where["source_id"]["$in"]
    assert s1.id in eligible
    assert s3.id in eligible
    assert s2.id not in eligible


# ---------------------------------------------------------------------------
# 4. Dedupe + rerank + per-source diversity cap
# ---------------------------------------------------------------------------


def test_dedupes_near_identical_quotes(session):
    """Near-identical quote text (whitespace differences) is deduplicated."""
    source = _make_source(session, title="Dup Source")
    chunks = [
        {"chunk_id": "c-0", "text": "Revenue grew  15%", "chunk_index": 0},
        {"chunk_id": "c-1", "text": "Revenue grew 15%", "chunk_index": 1},
    ]
    artifact = _make_content_artifact(session, source.id, chunks)

    meta0 = {
        "source_id": source.id,
        "artifact_id": artifact.id,
        "chunk_id": "c-0",
        "source_title": "Dup Source",
        "file_type": "csv",
        "team_label": "marketing",
        "category_labels": "[]",
        "period_start_month": "2026-01",
        "period_end_month": "2026-03",
        "content_type": "",
        "document_section": "",
        "chunk_index": 0,
    }
    meta1 = {**meta0, "chunk_id": "c-1", "chunk_index": 1}

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=["v0", "v1"],
        documents=["Revenue grew  15%", "Revenue grew 15%"],
        metadatas=[meta0, meta1],
        distances=[0.1, 0.12],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="revenue")

    assert not bundle.insufficient_evidence
    assert len(bundle.items) == 1  # deduped


def test_reranks_by_relevance_score(session):
    """Items are returned in relevance_score descending order."""
    source = _make_source(session, title="Ranked Source")
    chunks = [
        {"chunk_id": "c-0", "text": "Low relevance item", "chunk_index": 0},
        {"chunk_id": "c-1", "text": "High relevance item", "chunk_index": 1},
    ]
    artifact = _make_content_artifact(session, source.id, chunks)

    meta_lo = {
        "source_id": source.id,
        "artifact_id": artifact.id,
        "chunk_id": "c-0",
        "source_title": "Ranked Source",
        "file_type": "csv",
        "team_label": "marketing",
        "category_labels": "[]",
        "period_start_month": "2026-01",
        "period_end_month": "2026-03",
        "content_type": "",
        "document_section": "",
        "chunk_index": 0,
    }
    meta_hi = {**meta_lo, "chunk_id": "c-1", "chunk_index": 1}

    fake_collection = MagicMock()
    # distance 0.5 → relevance 0.5; distance 0.1 → relevance 0.9
    fake_collection.query.return_value = _chroma_result(
        ids=["v-lo", "v-hi"],
        documents=["Low relevance item", "High relevance item"],
        metadatas=[meta_lo, meta_hi],
        distances=[0.5, 0.1],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="relevance")

    assert len(bundle.items) == 2
    assert bundle.items[0].quote == "High relevance item"
    assert bundle.items[0].relevance_score > bundle.items[1].relevance_score


def test_per_source_diversity_cap(session):
    """max_chunks_per_source limits how many chunks per source are returned."""
    source = _make_source(session, title="Capped Source")
    chunks = [
        {"chunk_id": f"c-{i}", "text": f"Chunk {i} content unique", "chunk_index": i}
        for i in range(5)
    ]
    artifact = _make_content_artifact(session, source.id, chunks)

    metas = []
    for i in range(5):
        metas.append({
            "source_id": source.id,
            "artifact_id": artifact.id,
            "chunk_id": f"c-{i}",
            "source_title": "Capped Source",
            "file_type": "csv",
            "team_label": "marketing",
            "category_labels": "[]",
            "period_start_month": "2026-01",
            "period_end_month": "2026-03",
            "content_type": "",
            "document_section": "",
            "chunk_index": i,
        })

    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=[f"v-{i}" for i in range(5)],
        documents=[f"Chunk {i} content unique" for i in range(5)],
        metadatas=metas,
        distances=[0.1] * 5,
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(
            session,
            workspace_id=1,
            query="chunk",
            max_chunks_per_source=2,
        )

    assert not bundle.insufficient_evidence
    assert len(bundle.items) == 2  # capped at 2 per source


# ---------------------------------------------------------------------------
# 5. Low-quality retrieval returns insufficient evidence
# ---------------------------------------------------------------------------


def test_low_relevance_returns_insufficient_evidence(session):
    """When top relevance < min_relevance_score, bundle is insufficient."""
    source = _make_source(session, title="Low Rel Source")
    chunks = [{"chunk_id": "c-0", "text": "vague text", "chunk_index": 0}]
    artifact = _make_content_artifact(session, source.id, chunks)

    meta = {
        "source_id": source.id,
        "artifact_id": artifact.id,
        "chunk_id": "c-0",
        "source_title": "Low Rel Source",
        "file_type": "csv",
        "team_label": "marketing",
        "category_labels": "[]",
        "period_start_month": "2026-01",
        "period_end_month": "2026-03",
        "content_type": "",
        "document_section": "",
        "chunk_index": 0,
    }

    # distance 0.95 → relevance 0.05, below default min_relevance_score=0.2
    fake_collection = MagicMock()
    fake_collection.query.return_value = _chroma_result(
        ids=["v-low"],
        documents=["vague text"],
        metadatas=[meta],
        distances=[0.95],
    )

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="unrelated query")

    assert bundle.insufficient_evidence
    assert len(bundle.items) == 0
    assert "below threshold" in (bundle.reason or "")


def test_no_eligible_sources_returns_insufficient(session):
    """When no sources are eligible, returns insufficient with no items."""
    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=MagicMock()):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=999, query="anything")

    assert bundle.insufficient_evidence
    assert len(bundle.items) == 0
    assert "No eligible sources" in (bundle.reason or "")


def test_chromadb_unavailable_returns_insufficient(session):
    """When ChromaDB is None, returns insufficient gracefully."""
    _make_source(session)

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=None):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="test")

    assert bundle.insufficient_evidence
    assert "ChromaDB unavailable" in (bundle.reason or "")


def test_chroma_query_error_returns_insufficient(session):
    """When Chroma query raises (e.g. embedding failure), returns insufficient evidence."""
    _make_source(session)

    fake_collection = MagicMock()
    fake_collection.query.side_effect = RuntimeError("embedding API timeout")

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="test")

    assert bundle.insufficient_evidence
    assert "query error" in (bundle.reason or "").lower()
    assert len(bundle.items) == 0


def test_chroma_returns_empty_results(session):
    """When Chroma query returns no results, returns insufficient."""
    _make_source(session)

    fake_collection = MagicMock()
    fake_collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }

    with patch("app.knowledge.retrieval.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.retrieval import retrieve_company_knowledge

        bundle = retrieve_company_knowledge(session, workspace_id=1, query="test")

    assert bundle.insufficient_evidence
    assert "No vector candidates" in (bundle.reason or "")


# ---------------------------------------------------------------------------
# Agent tool wrapper
# ---------------------------------------------------------------------------


def test_agent_tool_wrapper_delegates_to_facade(session):
    """retrieve_company_knowledge_tool delegates correctly."""
    from app.knowledge.retrieval import EvidenceBundle, EvidenceItem

    mock_bundle = EvidenceBundle(
        items=[EvidenceItem(
            citation_id="v-0",
            source_id=1,
            artifact_id=1,
            chunk_id="c-0",
            source_title="Tool Source",
            file_type="csv",
            team_label="marketing",
            category_labels=[],
            period_start_month="2026-01",
            period_end_month="2026-03",
            quote="Tool evidence",
            page_number=None,
            row_refs=None,
            content_type="",
            document_section="",
            relevance_score=0.9,
        )],
    )

    with patch("app.agents.tools.retrieve_company_knowledge", return_value=mock_bundle) as mock_facade:
        from app.agents.tools import retrieve_company_knowledge_tool

        bundle = retrieve_company_knowledge_tool(session, workspace_id=1, query="tool test")

    mock_facade.assert_called_once_with(
        session, 1, "tool test", source_scope=None,
    )
    assert not bundle.insufficient_evidence
    assert len(bundle.items) == 1
    assert bundle.items[0].quote == "Tool evidence"
