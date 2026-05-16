"""PDF text extraction and insight-board generation.

Pipeline: OCR (Mistral) → Chunk (Chonkie) → Label chunks (OpenAI structured) → Aggregate (OpenAI structured) → Artifacts.
"""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import OpenAI as OpenAIClient
from sqlmodel import Session

from app.agents import extraction as llm_extraction
from app.core.config import get_settings
from app.knowledge.chunking import chunk_markdown
from app.models.enums import ArtifactType
from app.models.source import SourceData
from app.services.artifacts import get_source_artifact, upsert_source_artifact

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OCR helpers (mockable)
# ---------------------------------------------------------------------------


def _read_pdf_bytes(storage_path: str) -> bytes:
    """Read PDF file from storage path."""
    p = Path(storage_path)
    if not p.exists():
        raise FileNotFoundError(f"PDF file not found at: {storage_path}")
    return p.read_bytes()


def _check_file_size(content: bytes, max_mb: int) -> None:
    """Enforce maximum file size."""
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(f"PDF file size ({size_mb:.1f} MB) exceeds maximum ({max_mb} MB)")


def _run_mistral_ocr(api_key: str, pdf_b64: str) -> list[dict]:
    """Call Mistral OCR API and return list of page objects.

    Returns list of dicts with 'markdown' and 'index' keys (1-based).
    """
    from mistralai.client import Mistral

    client = Mistral(api_key=api_key)
    document_url = f"data:application/pdf;base64,{pdf_b64}"
    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": document_url},
        table_format="html",
        include_image_base64=False,
    )

    pages = []
    for page in response.pages:
        # Handle both object with attributes and dict-like access
        if hasattr(page, "markdown"):
            md = page.markdown
            idx = page.index if hasattr(page, "index") else 0
        elif isinstance(page, dict):
            md = page.get("markdown", "")
            idx = page.get("index", 0)
        else:
            md = str(page)
            idx = 0
        pages.append({"markdown": md, "index": idx})

    return pages


def _get_page_attr(page: Any, key: str, default: Any = None) -> Any:
    """Get attribute from page that may be a dict or object."""
    if isinstance(page, dict):
        return page.get(key, default)
    return getattr(page, key, default)


def _build_markdown_with_page_markers(pages: list[Any]) -> str:
    """Build markdown string with page markers from OCR results."""
    parts: list[str] = []
    for page in pages:
        idx = _get_page_attr(page, "index", 0)
        if idx == 0:
            idx = len(parts) + 1
        md = _get_page_attr(page, "markdown", "")
        if md:
            md = str(md).strip()
        if md:
            parts.append(f"<!-- page {idx} -->\n{md}")

    return "\n\n".join(parts)


def _count_meaningful_text(markdown: str) -> int:
    """Count meaningful (non-whitespace, non-marker) characters."""
    # Remove page markers
    cleaned = re.sub(r"<!-- page \d+ -->", "", markdown)
    # Remove whitespace
    cleaned = re.sub(r"\s+", "", cleaned)
    return len(cleaned)


# ---------------------------------------------------------------------------
# Chunk labeling helpers (OpenAI structured parsing)
# ---------------------------------------------------------------------------


def _label_all_chunks(chunks: list[str], client: OpenAIClient, model: str) -> list[dict]:
    """Label all chunks with metadata via ``llm_extraction.extract_chunk_label``."""
    labeled = []
    for index, chunk in enumerate(chunks):
        response = llm_extraction.extract_chunk_label(client, model, chunk, chunk_index=index)
        metadata = response.model_dump()
        metadata["chunk_index"] = index
        metadata["chunk_text"] = chunk
        metadata["page_numbers"] = _extract_page_numbers(chunk)
        labeled.append(metadata)
    return labeled


def _extract_page_numbers(text: str) -> list[int]:
    """Extract 1-based page markers from a chunk."""
    return [int(page) for page in re.findall(r"<!-- page (\d+) -->", text)]


def _aggregate_metadata(
    chunk_metadata: list[dict],
    page_count: int,
    ocr_md_path: str,
    chunks_path: str,
    model: str,
    client: OpenAIClient,
) -> tuple[dict, dict]:
    """Aggregate chunk metadata into source_summary and source_insight via ``llm_extraction.extract_aggregate``."""
    response = llm_extraction.extract_aggregate(
        client,
        model,
        chunk_metadata,
        page_count,
        ocr_md_path,
        chunks_path,
    )

    source_summary = response.source_summary.model_dump()
    source_insight = response.source_insight.model_dump()

    # Ensure summary has required fields
    source_summary["page_count"] = page_count
    source_summary["ocr_model"] = "mistral-ocr-latest"
    source_summary["structuring_model"] = model
    source_summary["extracted_markdown_path"] = ocr_md_path
    source_summary["chunk_metadata_path"] = chunks_path
    source_summary.setdefault("warnings", [])

    # Cap insight counts
    for key, cap in [("key_findings", 5), ("assumptions", 3), ("risks", 5), ("opportunities", 5), ("source_quotes", 5)]:
        items = source_insight.get(key, [])
        source_insight[key] = items[:cap]

    # Remove document_summary from insight if present
    source_insight.pop("document_summary", None)

    return source_summary, source_insight


# ---------------------------------------------------------------------------
# Main PDF processing
# ---------------------------------------------------------------------------


def _extracted_dir(workspace_id: int, source_id: int) -> Path:
    """Get the extraction output directory for a source."""
    base = Path("storage/extracted") / str(workspace_id) / str(source_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def process_pdf(session: Session, source: SourceData) -> None:
    """Full PDF processing pipeline: OCR → chunk → label → aggregate → artifacts.

    Raises on configuration or processing errors (caller should catch and mark Failed).
    """
    settings = get_settings()
    if source.id is None:
        raise ValueError("Source must be persisted before PDF processing")
    source_id = source.id

    # Validate config
    if not settings.rag_mistral_api_key:
        raise ValueError("RAG_MISTRAL_API_KEY is not configured. PDF processing requires Mistral OCR.")
    if not settings.rag_openai_api_key:
        raise ValueError("RAG_OPENAI_API_KEY is not configured. PDF processing requires an LLM for labeling.")

    # Create OpenAI client for structured extraction
    from app.core.openai_client import create_openai_client

    client = create_openai_client(
        api_key=settings.rag_openai_api_key,
        base_url=settings.rag_openai_api_base_url,
    )
    model = settings.rag_extraction_model

    # Read and validate file
    pdf_bytes = _read_pdf_bytes(source.storage_path)
    _check_file_size(pdf_bytes, settings.rag_max_file_size_mb)

    # OCR via Mistral
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    pages = _run_mistral_ocr(settings.rag_mistral_api_key, pdf_b64)

    # Build markdown with page markers
    markdown = _build_markdown_with_page_markers(pages)
    page_count = len(pages)

    # Save OCR markdown
    out_dir = _extracted_dir(source.workspace_id, source_id)
    ocr_md_path = out_dir / "ocr.md"
    ocr_md_path.write_text(markdown, encoding="utf-8")
    chunks_path = out_dir / "chunks.json"

    # Check for meaningful text
    meaningful_chars = _count_meaningful_text(markdown)
    if meaningful_chars < 500:
        # Short OCR: create source_summary and minimal source_content with warning
        warnings = [f"OCR extracted only {meaningful_chars} meaningful characters (threshold: 500). Document may be image-heavy or empty."]

        # Build minimal source_content from whatever text we have
        short_chunks: list[dict] = []
        if markdown.strip():
            short_chunks.append({
                "chunk_id": "pdf-short-0",
                "text": markdown[:2000].strip(),
                "content_type": "raw_text",
                "document_section": "unknown",
                "chunk_index": 0,
                "page_numbers": [1],
            })

        upsert_source_artifact(
            session,
            source_id,
            ArtifactType.SOURCE_SUMMARY,
            f"Summary: {source.title}",
            {
                "summary": markdown[:2000] if markdown else "(no extractable text)",
                "page_count": page_count,
                "ocr_model": "mistral-ocr-latest",
                "structuring_model": settings.rag_extraction_model,
                "extracted_markdown_path": str(ocr_md_path),
                "chunk_metadata_path": str(chunks_path),
                "warnings": warnings,
            },
        )

        # Create source_content even for short OCR (required for Ready gate)
        if short_chunks:
            upsert_source_artifact(
                session,
                source_id,
                ArtifactType.SOURCE_CONTENT,
                f"Content: {source.title}",
                {
                    "summary": f"Minimal content extracted ({meaningful_chars} chars).",
                    "statistics": {
                        "page_count": page_count,
                        "chunk_count": len(short_chunks),
                    },
                    "chunks": short_chunks,
                    "warnings": warnings,
                    "metadata": {
                        "ocr_model": "mistral-ocr-latest",
                        "extracted_markdown_path": str(ocr_md_path),
                    },
                },
            )

        chunks_path.write_text(json.dumps([], indent=2), encoding="utf-8")
        # Remove any existing source_insight artifact
        existing_insight = get_source_artifact(session, source_id, ArtifactType.SOURCE_INSIGHT)
        if existing_insight:
            session.delete(existing_insight)
        session.commit()
        return

    # Chunk markdown
    chunks = chunk_markdown(markdown)

    # Label each chunk
    chunk_metadata = _label_all_chunks(chunks, client, model)

    # Save chunk metadata
    chunks_path.write_text(json.dumps(chunk_metadata, indent=2), encoding="utf-8")

    # Aggregate into source_summary and source_insight
    source_summary, source_insight = _aggregate_metadata(
        chunk_metadata,
        page_count,
        str(ocr_md_path),
        str(chunks_path),
        model,
        client,
    )

    # Upsert artifacts via centralized service
    upsert_source_artifact(
        session,
        source_id,
        ArtifactType.SOURCE_SUMMARY,
        f"Summary: {source.title}",
        source_summary,
    )

    # Build source_content from labeled chunks with page references
    content_chunks: list[dict] = []
    for idx, cm in enumerate(chunk_metadata):
        chunk_text = cm.get("chunk_text", "")
        page_numbers = cm.get("page_numbers", [])
        quote = None
        notable_quotes = cm.get("notable_quotes", [])
        if notable_quotes and isinstance(notable_quotes, list):
            first_quote = notable_quotes[0] if notable_quotes else {}
            quote = first_quote.get("quote") if isinstance(first_quote, dict) else None
        content_chunks.append({
            "chunk_id": f"pdf-chunk-{idx}",
            "text": chunk_text,
            "quote": quote,
            "page_number": page_numbers[0] if page_numbers else None,
            "page_numbers": page_numbers,
            "content_type": cm.get("content_type", "raw_text"),
            "document_section": cm.get("document_section", "unknown"),
            "chunk_index": idx,
            "topics": cm.get("topics", []),
            "entities": cm.get("entities", []),
            "time_periods": cm.get("time_periods", []),
        })

    upsert_source_artifact(
        session,
        source_id,
        ArtifactType.SOURCE_CONTENT,
        f"Content: {source.title}",
        {
            "summary": source_summary.get("summary", ""),
            "statistics": {
                "page_count": page_count,
                "chunk_count": len(content_chunks),
            },
            "chunks": content_chunks,
            "warnings": [],
            "metadata": {
                "ocr_model": "mistral-ocr-latest",
                "structuring_model": settings.rag_extraction_model,
                "extracted_markdown_path": str(ocr_md_path),
                "chunk_metadata_path": str(chunks_path),
            },
        },
    )

    upsert_source_artifact(
        session,
        source_id,
        ArtifactType.SOURCE_INSIGHT,
        f"Insight: {source.title}",
        source_insight,
    )
    session.commit()
