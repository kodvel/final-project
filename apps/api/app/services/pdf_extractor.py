"""PDF text extraction and insight-board generation.

Pipeline: OCR (Mistral) → Chunk (Chonkie) → Label chunks (LiteLLM) → Aggregate (LiteLLM) → Artifacts.
"""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

from sqlmodel import Session

from app.core.config import get_settings
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
    from mistralai import Mistral

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
# Chunking helpers (mockable)
# ---------------------------------------------------------------------------


def _chunk_markdown(markdown: str, chunk_size: int = 3000, min_chars: int = 300) -> list[str]:
    """Chunk markdown text using Chonkie RecursiveChunker."""
    from chonkie import RecursiveChunker

    chunker = RecursiveChunker(tokenizer="character", chunk_size=chunk_size, min_characters_per_chunk=min_chars)
    chunks = chunker.chunk(markdown)
    return [chunk.text for chunk in chunks]


# ---------------------------------------------------------------------------
# LiteLLM labeling helpers (mockable)
# ---------------------------------------------------------------------------

CHUNK_LABEL_SYSTEM_PROMPT = """You are a document analysis assistant. Label the following text chunk with metadata.
Respond ONLY with valid JSON matching this schema:
{
  "document_section": "one allowed document_section label",
  "section_confidence": 0.0,
  "content_type": "narrative|table|metric|quote|assumption|risk|opportunity|recommendation|raw_text",
  "content_type_confidence": 0.0,
  "topics": ["topic1", "topic2"],
  "entities": ["entity1", "entity2"],
  "time_periods": ["period1"],
  "summary": "brief summary of chunk content",
  "notable_quotes": [{"quote": "verbatim quote", "page_number": 1}]
}
Allowed document_section labels: executive_summary, market_context, customer_insight, competitor_analysis,
financials, product_feature, risks, opportunities, recommendation, methodology, appendix, unknown.
Use only the allowed content_type labels. Use 0.0 to 1.0 numeric confidence scores."""

AGGREGATE_SYSTEM_PROMPT = """You are a document intelligence analyst. Given chunk metadata from a document, produce two JSON objects.

For source_summary:
{
  "summary": "overall document summary",
  "page_count": number,
  "ocr_model": "mistral-ocr-latest",
  "structuring_model": "provided_model_name",
  "extracted_markdown_path": "path",
  "chunk_metadata_path": "path",
  "warnings": []
}

For source_insight:
{
  "key_findings": [{"text": "finding", "page_number": null, "quote": null}, ...up to 5],
  "assumptions": [{"text": "assumption", "page_number": null, "quote": null}, ...up to 3],
  "risks": [{"text": "risk", "page_number": null, "quote": null}, ...up to 5],
  "opportunities": [{"text": "opportunity", "page_number": null, "quote": null}, ...up to 5],
  "source_quotes": [{"text": "quote", "page_number": null, "quote": "verbatim"}, ...up to 5]
}

Do NOT include a document_summary field in source_insight.
Respond with a single JSON object with keys "source_summary" and "source_insight"."""


def _call_litellm(system_prompt: str, user_content: str, api_base: str, api_key: str, model: str) -> str:
    """Make a single LiteLLM call and return the response text."""
    import litellm

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        api_base=api_base,
        api_key=api_key,
        temperature=0.1,
    )
    return response.choices[0].message.content


def _parse_json_with_repair(raw: str) -> Any:
    """Parse JSON string with one repair attempt."""
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to fix common issues: trailing commas
    fixed = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None


def _label_chunk(chunk_text: str, api_base: str, api_key: str, model: str) -> dict:
    """Label a single chunk with metadata using LiteLLM. One retry on failure."""
    last_error = None
    for attempt in range(2):
        try:
            raw = _call_litellm(CHUNK_LABEL_SYSTEM_PROMPT, chunk_text, api_base, api_key, model)
            parsed = _parse_json_with_repair(raw)
            if parsed is None:
                raise ValueError(f"Failed to parse chunk label JSON (attempt {attempt + 1})")
            if isinstance(parsed, list):
                parsed = parsed[0] if parsed else {}
            return parsed
        except Exception as e:
            last_error = e
            if attempt == 0:
                logger.warning("Chunk labeling failed (attempt 1), retrying: %s", e)
    raise RuntimeError(f"Chunk labeling failed after retry: {last_error}")


def _label_all_chunks(chunks: list[str], api_base: str, api_key: str, model: str) -> list[dict]:
    """Label all chunks with metadata."""
    labeled = []
    for index, chunk in enumerate(chunks):
        metadata = _label_chunk(chunk, api_base, api_key, model)
        metadata.setdefault("chunk_index", index)
        metadata.setdefault("chunk_text", chunk)
        metadata.setdefault("page_numbers", _extract_page_numbers(chunk))
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
    api_base: str,
    api_key: str,
) -> tuple[dict, dict]:
    """Aggregate chunk metadata into source_summary and source_insight using LiteLLM."""
    aggregate_input = json.dumps({
        "chunk_metadata": chunk_metadata,
        "page_count": page_count,
        "ocr_model": "mistral-ocr-latest",
        "structuring_model": model,
        "extracted_markdown_path": ocr_md_path,
        "chunk_metadata_path": chunks_path,
    })

    last_error = None
    for attempt in range(2):
        try:
            raw = _call_litellm(AGGREGATE_SYSTEM_PROMPT, aggregate_input, api_base, api_key, model)
            parsed = _parse_json_with_repair(raw)
            if parsed is None:
                raise ValueError(f"Failed to parse aggregate JSON (attempt {attempt + 1})")
            break
        except Exception as e:
            last_error = e
            if attempt == 0:
                logger.warning("Aggregate labeling failed (attempt 1), retrying: %s", e)
    else:
        raise RuntimeError(f"Aggregate labeling failed after retry: {last_error}")

    source_summary = parsed.get("source_summary", {})
    source_insight = parsed.get("source_insight", {})

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
                "structuring_model": settings.rag_openai_model,
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
    chunks = _chunk_markdown(markdown)

    # Label each chunk
    chunk_metadata = _label_all_chunks(
        chunks,
        settings.rag_openai_api_base_url,
        settings.rag_openai_api_key,
        settings.rag_openai_model,
    )

    # Save chunk metadata
    chunks_path.write_text(json.dumps(chunk_metadata, indent=2), encoding="utf-8")

    # Aggregate into source_summary and source_insight
    source_summary, source_insight = _aggregate_metadata(
        chunk_metadata,
        page_count,
        str(ocr_md_path),
        str(chunks_path),
        settings.rag_openai_model,
        settings.rag_openai_api_base_url,
        settings.rag_openai_api_key,
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
                "structuring_model": settings.rag_openai_model,
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
