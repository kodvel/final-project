"""Task 3 tests: PDF processing into source_summary, source_content, and source_insight artifacts."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import ArtifactType, ProcessingStatus


def create_workspace(client, name: str = "Demo") -> dict:
    response = client.post("/workspaces", json={"name": name, "description": "Test workspace"})
    assert response.status_code == 201
    return response.json()


def _mock_settings(**overrides):
    """Create a mock settings object with RAG defaults."""
    settings = MagicMock()
    settings.rag_mistral_api_key = "test-mistral-key"
    settings.rag_openai_api_base_url = "https://api.openai.com/v1"
    settings.rag_openai_api_key = "test-openai-key"
    settings.rag_openai_model = "google/gemini-3.1-flash-lite-preview"
    settings.rag_max_file_size_mb = 30
    for k, v in overrides.items():
        setattr(settings, k, v)
    return settings


# ---------------------------------------------------------------------------
# Unit tests for pdf_extractor helpers
# ---------------------------------------------------------------------------


def test_build_markdown_with_page_markers():
    from app.services.pdf_extractor import _build_markdown_with_page_markers

    pages = [
        {"markdown": "Page one content", "index": 1},
        {"markdown": "Page two content", "index": 2},
    ]
    result = _build_markdown_with_page_markers(pages)
    assert "<!-- page 1 -->" in result
    assert "<!-- page 2 -->" in result
    assert "Page one content" in result
    assert "Page two content" in result


def test_build_markdown_handles_zero_index():
    from app.services.pdf_extractor import _build_markdown_with_page_markers

    pages = [{"markdown": "Content", "index": 0}]
    result = _build_markdown_with_page_markers(pages)
    assert "<!-- page 1 -->" in result


def test_count_meaningful_text():
    from app.services.pdf_extractor import _count_meaningful_text

    md = "<!-- page 1 -->\nHello world\n\n<!-- page 2 -->\nMore text"
    count = _count_meaningful_text(md)
    # "HelloworldMoretext" = 18 chars
    assert count == 18


def test_count_meaningful_text_empty():
    from app.services.pdf_extractor import _count_meaningful_text

    assert _count_meaningful_text("") == 0
    assert _count_meaningful_text("   \n\n  ") == 0


def test_parse_json_with_repair_valid():
    from app.services.pdf_extractor import _parse_json_with_repair

    assert _parse_json_with_repair('{"key": "value"}') == {"key": "value"}


def test_parse_json_with_repair_code_block():
    from app.services.pdf_extractor import _parse_json_with_repair

    raw = '```json\n{"key": "value"}\n```'
    assert _parse_json_with_repair(raw) == {"key": "value"}


def test_parse_json_with_repair_trailing_comma():
    from app.services.pdf_extractor import _parse_json_with_repair

    raw = '{"key": "value",}'
    assert _parse_json_with_repair(raw) == {"key": "value"}


def test_parse_json_with_repair_invalid():
    from app.services.pdf_extractor import _parse_json_with_repair

    assert _parse_json_with_repair("not json at all") is None


def test_check_file_size_within_limit():
    from app.services.pdf_extractor import _check_file_size

    _check_file_size(b"x" * 100, 30)  # 100 bytes, well under 30 MB


def test_check_file_size_exceeds_limit():
    from app.services.pdf_extractor import _check_file_size

    with pytest.raises(ValueError, match="exceeds maximum"):
        _check_file_size(b"x" * (31 * 1024 * 1024), 30)


def test_upsert_artifact_creates_new():
    from app.services.artifacts import upsert_source_artifact

    session = MagicMock()
    session.exec.return_value.first.return_value = None

    upsert_source_artifact(session, 1, "source_summary", "Title", {"key": "val"})
    session.add.assert_called_once()


def test_upsert_artifact_updates_existing():
    from app.services.artifacts import upsert_source_artifact

    session = MagicMock()
    existing = MagicMock()
    session.exec.return_value.first.return_value = existing

    upsert_source_artifact(session, 1, "source_summary", "New Title", {"key": "new_val"})
    assert existing.title == "New Title"
    assert existing.content_json == {"key": "new_val"}
    session.add.assert_called_once_with(existing)


# ---------------------------------------------------------------------------
# Full pipeline tests with mocked external services
# ---------------------------------------------------------------------------


def _upload_pdf_source(client, workspace_id: int, pdf_content: bytes = b"%PDF-1.4 fake content") -> dict:
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace_id),
            "title": "Test PDF Report",
            "team_label": "business",
            "category_labels": ["competitor_analysis"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-03",
        },
        files={"file": ("report.pdf", pdf_content, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


@patch("app.services.pdf_extractor._call_litellm")
@patch("app.services.pdf_extractor._chunk_markdown")
@patch("app.services.pdf_extractor._run_mistral_ocr")
@patch("app.services.pdf_extractor.get_settings")
def test_pdf_creates_source_summary_and_insight_artifacts(
    mock_settings_fn, mock_ocr, mock_chunk, mock_litellm, client
):
    """PDF with sufficient OCR text creates source_summary, source_content, and source_insight artifacts."""
    mock_settings_fn.return_value = _mock_settings()

    # Mock OCR: 3 pages with meaningful content (>500 chars total after stripping whitespace)
    mock_ocr.return_value = [
        {
            "markdown": " ".join([
                "This is a detailed financial report with revenue figures and strategic analysis content.",
                "The company showed strong performance in Q1 2026 with revenue growth of 25% year-over-year.",
                "Key metrics include EBITDA margin improvement and customer acquisition cost optimization.",
            ]),
            "index": 1,
        },
        {
            "markdown": " ".join([
                "Market analysis shows growth trends in the technology sector with key competitive advantages.",
                "The team identified three major market segments worth pursuing for expansion.",
                "Asia-Pacific and European regions remain priority targets.",
            ]),
            "index": 2,
        },
        {
            "markdown": " ".join([
                "Risk factors include regulatory changes and market volatility affecting quarterly projections.",
                "The company has mitigation strategies in place including diversification and hedging approaches.",
                "These strategies apply to the upcoming fiscal year.",
            ]),
            "index": 3,
        },
    ]

    # Mock chunking: return 2 chunks
    mock_chunk.return_value = ["chunk one text about financials", "chunk two text about market analysis"]

    # Mock LiteLLM calls: first for chunk labels, then for aggregate
    chunk_label_1 = {
        "document_section": "financials",
        "section_confidence": 0.9,
        "content_type": "metric",
        "content_type_confidence": 0.9,
        "topics": ["revenue", "financials"],
        "entities": ["Company A"],
        "time_periods": ["Q1 2026"],
        "summary": "Financial overview with revenue figures",
        "notable_quotes": [{"quote": "Revenue grew 20%", "page_number": 1}],
    }
    chunk_label_2 = {
        "document_section": "market_context",
        "section_confidence": 0.9,
        "content_type": "narrative",
        "content_type_confidence": 0.9,
        "topics": ["market", "growth"],
        "entities": ["Sector Tech"],
        "time_periods": ["2026"],
        "summary": "Market analysis showing growth trends",
        "notable_quotes": [{"quote": "Growth is accelerating", "page_number": 2}],
    }
    aggregate_response = {
        "source_summary": {
            "summary": "A financial and market analysis report.",
            "page_count": 3,
            "ocr_model": "mistral-ocr-latest",
            "structuring_model": "google/gemini-3.1-flash-lite-preview",
            "extracted_markdown_path": "/some/path/ocr.md",
            "chunk_metadata_path": "/some/path/chunks.json",
            "warnings": [],
        },
        "source_insight": {
            "key_findings": [{"text": "Revenue up 20%", "page_number": 1, "quote": "Revenue grew 20%"}],
            "assumptions": [{"text": "Market continues growing", "page_number": 2, "quote": None}],
            "risks": [{"text": "Regulatory risk", "page_number": 3, "quote": None}],
            "opportunities": [{"text": "Tech sector growth", "page_number": 2, "quote": None}],
            "source_quotes": [{"text": "Growth accelerating", "page_number": 2, "quote": "Growth is accelerating"}],
        },
    }

    mock_litellm.side_effect = [
        json.dumps(chunk_label_1),  # label chunk 1
        json.dumps(chunk_label_2),  # label chunk 2
        json.dumps(aggregate_response),  # aggregate
    ]

    workspace = create_workspace(client)
    source = _upload_pdf_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY, source.get("processing_error")

    # Check artifacts
    viz = client.get(f"/visualizations/{source['id']}").json()
    artifact_types = {a["artifact_type"] for a in viz}
    assert "source_summary" in artifact_types
    assert "source_content" in artifact_types
    assert "source_insight" in artifact_types

    # Verify source_summary content
    summary = next(a for a in viz if a["artifact_type"] == "source_summary")
    assert "summary" in summary["content_json"]
    assert summary["content_json"]["page_count"] == 3
    assert Path(summary["content_json"]["extracted_markdown_path"]).exists()
    assert Path(summary["content_json"]["chunk_metadata_path"]).exists()

    # Verify source_content has chunks with proper structure
    content = next(a for a in viz if a["artifact_type"] == "source_content")
    assert "chunks" in content["content_json"]
    assert len(content["content_json"]["chunks"]) == 2
    first_chunk = content["content_json"]["chunks"][0]
    assert "chunk_id" in first_chunk
    assert first_chunk["chunk_id"] == "pdf-chunk-0"
    assert "text" in first_chunk
    assert "document_section" in first_chunk
    assert "content_type" in first_chunk
    assert "chunk_index" in first_chunk
    assert first_chunk["chunk_index"] == 0

    # Verify source_insight
    insight = next(a for a in viz if a["artifact_type"] == "source_insight")
    assert "key_findings" in insight["content_json"]
    assert "document_summary" not in insight["content_json"]


@patch("app.services.pdf_extractor._call_litellm")
@patch("app.services.pdf_extractor._chunk_markdown")
@patch("app.services.pdf_extractor._run_mistral_ocr")
@patch("app.services.pdf_extractor.get_settings")
def test_short_ocr_creates_summary_and_content_warning_no_insight(
    mock_settings_fn, mock_ocr, mock_chunk, mock_litellm, client
):
    """PDF with <500 meaningful chars creates source_summary and source_content with warning, no source_insight."""
    mock_settings_fn.return_value = _mock_settings()

    # Mock OCR: page with short but non-empty content
    mock_ocr.return_value = [
        {"markdown": "Short text", "index": 1},
    ]

    workspace = create_workspace(client)
    source = _upload_pdf_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY, source.get("processing_error")

    # Check artifacts: source_summary and source_content, no source_insight
    viz = client.get(f"/visualizations/{source['id']}").json()
    artifact_types = {a["artifact_type"] for a in viz}
    assert "source_summary" in artifact_types
    assert "source_content" in artifact_types
    assert "source_insight" not in artifact_types

    summary = next(a for a in viz if a["artifact_type"] == "source_summary")
    assert len(summary["content_json"]["warnings"]) > 0
    assert "500" in summary["content_json"]["warnings"][0]
    assert Path(summary["content_json"]["extracted_markdown_path"]).exists()
    assert Path(summary["content_json"]["chunk_metadata_path"]).exists()
    assert json.loads(Path(summary["content_json"]["chunk_metadata_path"]).read_text()) == []

    content = next(a for a in viz if a["artifact_type"] == "source_content")
    assert "chunks" in content["content_json"]
    assert len(content["content_json"]["chunks"]) > 0


@patch("app.services.pdf_extractor._run_mistral_ocr")
@patch("app.services.pdf_extractor.get_settings")
def test_ocr_failure_marks_source_failed(mock_settings_fn, mock_ocr, client):
    """OCR failure should mark source as Failed."""
    mock_settings_fn.return_value = _mock_settings()
    mock_ocr.side_effect = RuntimeError("Mistral API error")

    workspace = create_workspace(client)
    source = _upload_pdf_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.FAILED
    assert "RuntimeError" in source["processing_error"]


@patch("app.services.pdf_extractor.get_settings")
def test_missing_mistral_key_marks_source_failed(mock_settings_fn, client):
    """Missing RAG_MISTRAL_API_KEY should mark source as Failed."""
    mock_settings_fn.return_value = _mock_settings(rag_mistral_api_key=None)

    workspace = create_workspace(client)
    source = _upload_pdf_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.FAILED
    assert "RAG_MISTRAL_API_KEY" in source["processing_error"]


@patch("app.services.pdf_extractor.get_settings")
def test_missing_openai_key_marks_source_failed(mock_settings_fn, client):
    """Missing RAG_OPENAI_API_KEY should mark source as Failed."""
    mock_settings_fn.return_value = _mock_settings(rag_openai_api_key=None)

    workspace = create_workspace(client)
    source = _upload_pdf_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.FAILED
    assert "RAG_OPENAI_API_KEY" in source["processing_error"]


@patch("app.services.pdf_extractor._call_litellm")
@patch("app.services.pdf_extractor._chunk_markdown")
@patch("app.services.pdf_extractor._run_mistral_ocr")
@patch("app.services.pdf_extractor.get_settings")
def test_ocr_handles_page_objects_with_attributes(
    mock_settings_fn, mock_ocr, mock_chunk, mock_litellm, client
):
    """OCR should handle Mistral response pages as both objects and dicts."""
    mock_settings_fn.return_value = _mock_settings()

    # Create mock page objects (attribute access, not dict)
    class MockPage:
        def __init__(self, markdown, index):
            self.markdown = markdown
            self.index = index

    mock_ocr.return_value = [
        MockPage(
            "Detailed financial analysis report with comprehensive data on revenue streams, market positioning, "
            "and competitive advantages in the technology sector.",
            1,
        ),
        MockPage(
            "Strategic recommendations for growth include expanding into emerging markets and investing in AI "
            "capabilities for long-term competitive positioning.",
            2,
        ),
    ]

    mock_chunk.return_value = ["chunk text about financials and revenue analysis"]
    aggregate_response = {
        "source_summary": {
            "summary": "Financial analysis report.",
            "page_count": 2,
            "ocr_model": "mistral-ocr-latest",
            "structuring_model": "google/gemini-3.1-flash-lite-preview",
            "extracted_markdown_path": "/path/ocr.md",
            "chunk_metadata_path": "/path/chunks.json",
            "warnings": [],
        },
        "source_insight": {
            "key_findings": [],
            "assumptions": [],
            "risks": [],
            "opportunities": [],
            "source_quotes": [],
        },
    }
    mock_litellm.side_effect = [
        json.dumps({
            "document_section": "financials",
            "section_confidence": 0.9,
            "content_type": "narrative",
            "content_type_confidence": 0.9,
            "topics": ["finance"],
            "entities": [],
            "time_periods": [],
            "summary": "Financial analysis",
            "notable_quotes": [],
        }),
        json.dumps(aggregate_response),
    ]

    workspace = create_workspace(client)
    source = _upload_pdf_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY, source.get("processing_error")

    # Verify source_content was created with chunks from labeled pages
    viz = client.get(f"/visualizations/{source['id']}").json()
    artifact_types = {a["artifact_type"] for a in viz}
    assert "source_content" in artifact_types
    content = next(a for a in viz if a["artifact_type"] == "source_content")
    assert len(content["content_json"]["chunks"]) == 1


# ---------------------------------------------------------------------------
# Enum contract tests (ensure updated values)
# ---------------------------------------------------------------------------


def test_artifact_type_source_summary_value():
    assert ArtifactType.SOURCE_SUMMARY == "source_summary"


def test_artifact_type_source_insight_value():
    assert ArtifactType.SOURCE_INSIGHT == "source_insight"


def test_no_legacy_pdf_enums():
    """Ensure old PDF_SUMMARY, PDF_INSIGHT_BOARD, and retired CSV enums are removed."""
    member_names = {m.name for m in ArtifactType}
    assert "PDF_SUMMARY" not in member_names
    assert "PDF_INSIGHT_BOARD" not in member_names
    assert "CSV_PROFILE" not in member_names
    assert "CHART_SPEC" not in member_names
    assert "INSIGHT_CARD" not in member_names


# ---------------------------------------------------------------------------
# Ready gate tests
# ---------------------------------------------------------------------------


def test_ready_gate_requires_source_content_csv(client) -> None:
    """CSV source must have both source_summary and source_content to be Ready."""
    from unittest.mock import patch

    workspace = create_workspace(client)

    # Upload valid CSV
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Gate test",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-01",
        },
        files={"file": ("data.csv", b"col1,col2\n1,2\n3,4\n", "text/csv")},
    )
    assert response.status_code == 201
    source = response.json()
    assert source["processing_status"] == ProcessingStatus.READY

    # Verify both artifacts exist
    viz = client.get(f"/visualizations/{source['id']}").json()
    artifact_types = {a["artifact_type"] for a in viz}
    assert "source_summary" in artifact_types
    assert "source_content" in artifact_types


def test_csv_source_content_chunks_have_stable_ids(client) -> None:
    """CSV source_content chunks should have stable chunk_ids and column references."""
    workspace = create_workspace(client)
    csv_content = "month,revenue,region\n2026-01,1000,North\n2026-02,1500,South\n"
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Chunk ID test",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-02",
        },
        files={"file": ("data.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 201
    source = response.json()
    assert source["processing_status"] == ProcessingStatus.READY

    viz = client.get(f"/visualizations/{source['id']}").json()
    content = next(a for a in viz if a["artifact_type"] == "source_content")
    chunks = content["content_json"]["chunks"]

    # Each chunk should have a stable chunk_id
    chunk_ids = [c["chunk_id"] for c in chunks]
    assert all(cid.startswith("csv-profile-") for cid in chunk_ids)
    # Chunk IDs should be unique
    assert len(chunk_ids) == len(set(chunk_ids))
    # Each chunk should have chunk_index, text, content_type, document_section
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "text" in chunk
        assert "content_type" in chunk
        assert "document_section" in chunk
        assert "chunk_index" in chunk
        assert "columns" in chunk
