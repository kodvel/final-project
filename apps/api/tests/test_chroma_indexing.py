"""Tests for ChromaDB indexing of source_content chunks (migration slice 4)."""

import json
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


# ---------------------------------------------------------------------------
# Unit tests: _OpenAIEmbeddingFunction
# ---------------------------------------------------------------------------


def test_embedding_function_calls_openai():
    """_OpenAIEmbeddingFunction creates an OpenAI client and returns vectors."""
    from app.knowledge.chroma import _OpenAIEmbeddingFunction

    fake_embedding = [0.1] * 1536
    fake_item = MagicMock()
    fake_item.embedding = fake_embedding
    fake_item.index = 0
    fake_response = MagicMock()
    fake_response.data = [fake_item]

    ef = _OpenAIEmbeddingFunction(
        api_base_url="https://api.example.com/v1",
        api_key="test-key",
        model="text-embedding-3-small",
    )

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = fake_response
        mock_openai_cls.return_value = mock_client

        result = ef(["hello world"])

    assert len(result) == 1
    assert result[0] == fake_embedding
    mock_openai_cls.assert_called_once_with(
        base_url="https://api.example.com/v1",
        api_key="test-key",
    )
    mock_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input=["hello world"],
    )


def test_embedding_function_batch():
    """_OpenAIEmbeddingFunction handles batch input."""
    from app.knowledge.chroma import _OpenAIEmbeddingFunction

    fake_items = []
    for i in range(3):
        item = MagicMock()
        item.embedding = [float(i)] * 1536
        item.index = i
        fake_items.append(item)
    fake_response = MagicMock()
    fake_response.data = fake_items

    ef = _OpenAIEmbeddingFunction(
        api_base_url="https://api.example.com/v1",
        api_key="test-key",
        model="text-embedding-3-small",
    )

    with patch("openai.OpenAI", return_value=MagicMock()) as mock_openai_cls:
        mock_openai_cls.return_value.embeddings.create.return_value = fake_response
        result = ef(["a", "b", "c"])

    assert len(result) == 3


def test_embedding_function_returns_empty_for_empty_input():
    """_OpenAIEmbeddingFunction returns [] for empty input (no API call)."""
    from app.knowledge.chroma import _OpenAIEmbeddingFunction

    ef = _OpenAIEmbeddingFunction(
        api_base_url="https://api.example.com/v1",
        api_key="test-key",
        model="text-embedding-3-small",
    )
    result = ef([])
    assert result == []


def test_embedding_function_sorts_by_index():
    """_OpenAIEmbeddingFunction sorts results by index to match input order."""
    from app.knowledge.chroma import _OpenAIEmbeddingFunction

    # Return items out of order
    item1 = MagicMock()
    item1.embedding = [0.1] * 1536
    item1.index = 1
    item0 = MagicMock()
    item0.embedding = [0.2] * 1536
    item0.index = 0
    fake_response = MagicMock()
    fake_response.data = [item1, item0]

    ef = _OpenAIEmbeddingFunction(
        api_base_url="https://api.example.com/v1",
        api_key="test-key",
        model="text-embedding-3-small",
    )

    with patch("openai.OpenAI", return_value=MagicMock()) as mock_openai_cls:
        mock_openai_cls.return_value.embeddings.create.return_value = fake_response
        result = ef(["a", "b"])

    # Sorted: index 0 first, then index 1
    assert result[0] == [0.2] * 1536
    assert result[1] == [0.1] * 1536


# ---------------------------------------------------------------------------
# Unit tests: _build_embedding_function
# ---------------------------------------------------------------------------


def test_build_embedding_function_returns_ef_with_key():
    """_build_embedding_function returns function when API key is configured."""
    from app.knowledge.chroma import _build_embedding_function

    fake_settings = MagicMock()
    fake_settings.rag_embedding_api_base_url = "https://api.example.com/v1"
    fake_settings.rag_embedding_api_key = "test-key"
    fake_settings.rag_embedding_model = "text-embedding-3-small"

    with patch("app.core.config.get_settings", return_value=fake_settings):
        ef = _build_embedding_function()

    assert ef is not None


def test_build_embedding_function_returns_none_without_key():
    """_build_embedding_function returns None when API key is missing."""
    from app.knowledge.chroma import _build_embedding_function

    fake_settings = MagicMock()
    fake_settings.rag_embedding_api_key = None

    with patch("app.core.config.get_settings", return_value=fake_settings):
        ef = _build_embedding_function()

    assert ef is None


# ---------------------------------------------------------------------------
# Unit tests: index_source_content
# ---------------------------------------------------------------------------


def test_index_source_content_csv_chunks(session):
    """CSV source_content chunks are indexed with stable IDs and metadata."""
    source = _make_source(session, title="Revenue Data")
    _make_categories(session, source.id, ["analytics_metrics", "revenue_sales"])
    chunks = [
        {
            "chunk_id": "csv-profile-0",
            "text": "Column 'revenue' (numeric): ranges 100.00–500.00, avg 250.00",
            "content_type": "metric",
            "document_section": "data_profile",
            "chunk_index": 0,
            "columns": ["revenue"],
        },
        {
            "chunk_id": "csv-profile-1",
            "text": "Column 'month' (date): spans 2026-01 to 2026-03",
            "content_type": "metadata",
            "document_section": "data_profile",
            "chunk_index": 1,
            "columns": ["month"],
        },
    ]
    artifact = _make_content_artifact(session, source.id, chunks)

    fake_collection = MagicMock()
    fake_collection.upsert = MagicMock()

    with patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.indexing import index_source_content

        count = index_source_content(session, source.id)

    assert count == 2
    fake_collection.upsert.assert_called_once()
    call_kwargs = fake_collection.upsert.call_args[1]
    ids = call_kwargs["ids"]
    docs = call_kwargs["documents"]
    metas = call_kwargs["metadatas"]

    # upsert should NOT include embeddings (Chroma auto-embeds)
    assert "embeddings" not in call_kwargs

    # Stable IDs
    assert ids[0] == f"source:{source.id}:artifact:{artifact.id}:chunk:0"
    assert ids[1] == f"source:{source.id}:artifact:{artifact.id}:chunk:1"

    # Documents are chunk texts
    assert docs[0] == chunks[0]["text"]
    assert docs[1] == chunks[1]["text"]

    # Metadata includes source fields
    meta0 = metas[0]
    assert meta0["source_id"] == source.id
    assert meta0["source_title"] == "Revenue Data"
    assert meta0["file_type"] == "csv"
    assert meta0["team_label"] == "marketing"
    assert json.loads(meta0["category_labels"]) == ["analytics_metrics", "revenue_sales"]
    assert meta0["period_start_month"] == "2026-01"
    assert meta0["period_end_month"] == "2026-03"
    assert meta0["content_type"] == "metric"
    assert meta0["document_section"] == "data_profile"
    assert meta0["chunk_index"] == 0
    assert json.loads(meta0["columns"]) == ["revenue"]


def test_index_source_content_pdf_with_page_metadata(session):
    """PDF source_content chunks include page_number in metadata."""
    source = _make_source(session, file_type=SourceFileType.PDF, title="Brief")
    chunks = [
        {
            "chunk_id": "pdf-chunk-0",
            "text": "Executive summary of the report",
            "content_type": "narrative",
            "document_section": "executive_summary",
            "chunk_index": 0,
            "page_number": 1,
            "page_numbers": [1],
        },
        {
            "chunk_id": "pdf-chunk-1",
            "text": "Financial details on page 2",
            "content_type": "metric",
            "document_section": "financials",
            "chunk_index": 1,
            "page_number": 2,
            "page_numbers": [2],
        },
    ]
    _make_content_artifact(session, source.id, chunks)

    fake_collection = MagicMock()
    with patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.indexing import index_source_content

        count = index_source_content(session, source.id)

    assert count == 2
    call_metas = fake_collection.upsert.call_args[1]["metadatas"]
    assert call_metas[0]["page_number"] == 1
    assert call_metas[1]["page_number"] == 2


def test_index_source_content_skips_empty_chunks(session):
    """Chunks with empty text are skipped."""
    source = _make_source(session)
    chunks = [
        {"chunk_id": "c-0", "text": "Real content", "chunk_index": 0},
        {"chunk_id": "c-1", "text": "   ", "chunk_index": 1},
        {"chunk_id": "c-2", "text": "", "chunk_index": 2},
    ]
    _make_content_artifact(session, source.id, chunks)

    fake_collection = MagicMock()
    with patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.indexing import index_source_content

        count = index_source_content(session, source.id)

    assert count == 1


def test_index_source_content_no_artifact_raises(session):
    """Indexing a source with no source_content artifact raises ValueError."""
    source = _make_source(session)

    from app.knowledge.indexing import index_source_content

    with pytest.raises(ValueError, match="No source_content artifact"):
        index_source_content(session, source.id)


def test_index_source_content_collection_unavailable(session):
    """When ChromaDB is unavailable, indexing returns 0 gracefully."""
    source = _make_source(session)
    chunks = [{"chunk_id": "c-0", "text": "some text", "chunk_index": 0}]
    _make_content_artifact(session, source.id, chunks)

    with patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=None):
        from app.knowledge.indexing import index_source_content

        count = index_source_content(session, source.id)

    assert count == 0


# ---------------------------------------------------------------------------
# Unit tests: delete_source_vectors
# ---------------------------------------------------------------------------


def test_delete_source_vectors_calls_collection_delete():
    fake_collection = MagicMock()
    with patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.indexing import delete_source_vectors

        delete_source_vectors(42)

    fake_collection.delete.assert_called_once_with(where={"source_id": 42})


def test_delete_source_vectors_noop_when_chroma_unavailable():
    with patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=None):
        from app.knowledge.indexing import delete_source_vectors

        # Should not raise
        delete_source_vectors(42)


# ---------------------------------------------------------------------------
# Unit tests: reindex_source_content
# ---------------------------------------------------------------------------


def test_reindex_deletes_then_indexes(session):
    """reindex_source_content deletes old vectors then indexes fresh."""
    source = _make_source(session)
    chunks = [{"chunk_id": "c-0", "text": "updated text", "chunk_index": 0}]
    _make_content_artifact(session, source.id, chunks)

    fake_collection = MagicMock()
    with patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=fake_collection):
        from app.knowledge.indexing import reindex_source_content

        count = reindex_source_content(session, source.id)

    assert count == 1
    # delete called before upsert
    assert fake_collection.delete.called
    assert fake_collection.upsert.called


def test_retry_replaces_vectors(session):
    """Re-processing a source replaces its vectors (delete + re-index)."""
    source = _make_source(session, processing_status=ProcessingStatus.FAILED)
    chunks = [{"chunk_id": "c-0", "text": "retry content", "chunk_index": 0}]
    _make_content_artifact(session, source.id, chunks)

    # Also need source_summary for Ready gate
    summary = SourceArtifact(
        source_id=source.id,
        artifact_type=str(ArtifactType.SOURCE_SUMMARY),
        title="Summary",
        content_json={"summary": "test"},
    )
    session.add(summary)
    session.commit()

    fake_collection = MagicMock()
    with (
        patch("app.knowledge.indexing.get_company_knowledge_collection", return_value=fake_collection),
        patch("app.knowledge.indexing.index_source_content", return_value=1) as mock_index,
        patch("app.knowledge.indexing.delete_source_vectors") as mock_delete,
        patch("app.services.source_processing._process_csv"),
    ):
        from app.services.source_processing import process_source

        result = process_source(session, source.id)

    assert result.processing_status == ProcessingStatus.READY
    mock_delete.assert_called_with(source.id)
    mock_index.assert_called_once_with(session, source.id)


# ---------------------------------------------------------------------------
# Integration: soft delete removes vectors
# ---------------------------------------------------------------------------


def test_soft_delete_removes_vectors():
    """soft_delete_source calls delete_source_vectors."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        source = SourceData(
            workspace_id=1,
            title="Del",
            team_label=TeamLabel.BUSINESS,
            file_type=SourceFileType.CSV,
            original_filename="d.csv",
            storage_path="/tmp/d.csv",
            period_start_month="2026-01",
            period_end_month="2026-01",
        )
        session.add(source)
        session.commit()
        session.refresh(source)
        source_id = source.id

        with patch("app.knowledge.indexing.delete_source_vectors") as mock_delete:
            from app.services.sources import soft_delete_source

            result = soft_delete_source(session, source_id)

        assert result.deleted_at is not None
        mock_delete.assert_called_once_with(source_id)

    engine.dispose()


# ---------------------------------------------------------------------------
# Integration: indexing failure marks source failed
# ---------------------------------------------------------------------------


def test_indexing_failure_marks_source_failed(session):
    """If indexing raises, source should be marked Failed."""
    source = _make_source(session, processing_status=ProcessingStatus.UPLOADED)

    chunks = [{"chunk_id": "c-0", "text": "content", "chunk_index": 0}]
    _make_content_artifact(session, source.id, chunks)

    summary = SourceArtifact(
        source_id=source.id,
        artifact_type=str(ArtifactType.SOURCE_SUMMARY),
        title="Summary",
        content_json={"summary": "test"},
    )
    session.add(summary)
    session.commit()

    with (
        patch("app.services.source_processing._process_csv"),
        patch("app.knowledge.indexing.delete_source_vectors"),
        patch("app.knowledge.indexing.index_source_content", side_effect=RuntimeError("chroma error")),
    ):
        from app.services.source_processing import process_source

        result = process_source(session, source.id)

    assert result.processing_status == ProcessingStatus.FAILED
    assert "chroma error" in (result.processing_error or "")
