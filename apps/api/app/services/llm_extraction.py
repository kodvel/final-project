"""Shared LLM extraction service using OpenAI structured parsing.

Replaces manual LiteLLM calls and JSON repair logic with
``client.chat.completions.parse(..., response_format=PydanticModel)``.

All extraction functions accept an *OpenAI client instance* so that callers
control client lifecycle and tests can inject mocks without touching settings.
"""

import json
import logging
from typing import TypeVar

from openai import OpenAI as OpenAIClient
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Generic structured extraction
# ---------------------------------------------------------------------------


def extract_structured(
    client: OpenAIClient,
    model: str,
    system_prompt: str,
    user_content: str,
    response_format: type[T],
    temperature: float = 0.1,
    retries: int = 1,
    name: str | None = None,
    metadata: dict | None = None,
) -> T:
    """Extract structured data via ``client.chat.completions.parse()``.

    Args:
        client: Configured *OpenAI* client.
        model: Model identifier forwarded to the API.
        system_prompt: System message.
        user_content: User message.
        response_format: Pydantic class used as ``response_format``.
        temperature: Sampling temperature.
        retries: Extra attempts after the first failure.
        name: Optional Langfuse observation name for this call.
        metadata: Optional Langfuse metadata dict for this call.

    Returns:
        Validated Pydantic model instance.

    Raises:
        RuntimeError: If every attempt fails.
    """
    last_error: Exception | None = None
    extra_kwargs: dict = {}
    if name is not None:
        extra_kwargs["name"] = name
    if metadata is not None:
        extra_kwargs["metadata"] = metadata
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format=response_format,
                temperature=temperature,
                **extra_kwargs,
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                raise ValueError(f"LLM returned no structured output (attempt {attempt + 1})")
            return parsed
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                logger.warning(
                    "Structured extraction failed (attempt %d/%d), retrying: %s",
                    attempt + 1,
                    retries + 1,
                    exc,
                )
    raise RuntimeError(f"Structured extraction failed after {retries + 1} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

# --- Chunk labeling (PDF) ---


class NotableQuote(BaseModel):
    """A notable quote extracted from a document chunk."""

    quote: str
    page_number: int | None = None


class ChunkLabelResponse(BaseModel):
    """Structured response for PDF chunk labeling."""

    document_section: str = "unknown"
    section_confidence: float = 0.0
    content_type: str = "raw_text"
    content_type_confidence: float = 0.0
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    time_periods: list[str] = Field(default_factory=list)
    summary: str = ""
    notable_quotes: list[NotableQuote] = Field(default_factory=list)


# --- Aggregate (PDF source_summary + source_insight) ---


class CitationItem(BaseModel):
    """A citation-ready item with optional page reference."""

    text: str
    page_number: int | None = None
    quote: str | None = None


class SourceSummaryExtract(BaseModel):
    """Structured extraction for PDF source_summary."""

    summary: str = ""
    page_count: int = 0
    ocr_model: str = "mistral-ocr-latest"
    structuring_model: str = ""
    extracted_markdown_path: str = ""
    chunk_metadata_path: str = ""
    warnings: list[str] = Field(default_factory=list)


class SourceInsightExtract(BaseModel):
    """Structured extraction for PDF source_insight."""

    key_findings: list[CitationItem] = Field(default_factory=list)
    assumptions: list[CitationItem] = Field(default_factory=list)
    risks: list[CitationItem] = Field(default_factory=list)
    opportunities: list[CitationItem] = Field(default_factory=list)
    source_quotes: list[CitationItem] = Field(default_factory=list)


class AggregateResponse(BaseModel):
    """Combined response for PDF aggregate extraction."""

    source_summary: SourceSummaryExtract
    source_insight: SourceInsightExtract


# --- CSV content extraction ---


class CSVContentChunk(BaseModel):
    """A chunk in CSV source_content."""

    chunk_id: str
    text: str
    content_type: str
    document_section: str
    chunk_index: int
    columns: list[str] = Field(default_factory=list)


class CSVContentResponse(BaseModel):
    """Structured response for CSV source_content extraction."""

    summary: str = ""
    statistics: dict = Field(default_factory=dict)
    chunks: list[CSVContentChunk] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


# --- CSV insight extraction ---


class FindingItem(BaseModel):
    """A finding, risk, or opportunity item."""

    text: str
    confidence: str = "medium"


class CSVInsightResponse(BaseModel):
    """Structured response for CSV source_insight extraction."""

    findings: list[FindingItem] = Field(default_factory=list)
    risks: list[FindingItem] = Field(default_factory=list)
    opportunities: list[FindingItem] = Field(default_factory=list)
    assumptions: list[FindingItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

CHUNK_LABEL_SYSTEM_PROMPT = """\
You are a document analysis assistant. Label the following text chunk with metadata.

Allowed document_section labels:
executive_summary, market_context, customer_insight, competitor_analysis,
financials, product_feature, risks, opportunities, recommendation,
methodology, appendix, unknown.

Allowed content_type labels:
narrative, table, metric, quote, assumption, risk, opportunity,
recommendation, raw_text.

Provide confidence scores between 0.0 and 1.0.
List relevant topics, entities, and time_periods.
Include any notable quotes with page numbers if present."""

AGGREGATE_SYSTEM_PROMPT = """\
You are a document intelligence analyst. Given chunk metadata from a document, \
produce a source_summary and source_insight.

For source_summary: provide an overall document summary, page count, and any warnings.

For source_insight: provide up to 5 key findings, up to 3 assumptions, up to 5 risks, \
up to 5 opportunities, and up to 5 source quotes. Each item should include text, \
page_number (if known), and quote (verbatim if available).

Do NOT include a document_summary field in source_insight."""

CSV_CONTENT_SYSTEM_PROMPT = """\
You are a data analysis assistant. Given CSV profiling data (column types, \
statistics, row counts), generate searchable content chunks.

Each chunk should be a factual, retrieval-friendly text snippet describing a \
specific aspect of the dataset.
Use these content_type values: metric, metadata, narrative.
Use these document_section values: data_profile, data_summary, data_overview, data_quality.

For each chunk include a columns list with the column names that chunk describes.

Ensure chunks cover:
- Individual column profiles (type, stats, ranges)
- Overall dataset summary (row/column counts, key metrics)
- Data quality observations

Use stable chunk_id values like csv-llm-0, csv-llm-1, etc."""

CSV_INSIGHT_SYSTEM_PROMPT = """\
You are a data analysis assistant. Given CSV profiling data, identify insights, \
risks, opportunities, and assumptions.

Focus on:
- Key statistical findings (ranges, averages, distributions)
- Data quality risks (high null rates, outliers, limited coverage)
- Opportunities (strong metrics, useful segmentations, trends)
- Assumptions about the data

Keep findings factual and grounded in the provided statistics. \
Each item should include a confidence level (high, medium, low)."""


# ---------------------------------------------------------------------------
# High-level extraction functions
# ---------------------------------------------------------------------------


def extract_chunk_label(
    client: OpenAIClient,
    model: str,
    chunk_text: str,
    chunk_index: int | None = None,
) -> ChunkLabelResponse:
    """Label a single PDF chunk using structured extraction (1 retry)."""
    metadata = {"stage": "pdf.label_chunk"}
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index
    return extract_structured(
        client=client,
        model=model,
        system_prompt=CHUNK_LABEL_SYSTEM_PROMPT,
        user_content=chunk_text,
        response_format=ChunkLabelResponse,
        retries=1,
        name="pdf.label_chunk",
        metadata=metadata,
    )


def extract_aggregate(
    client: OpenAIClient,
    model: str,
    chunk_metadata: list[dict],
    page_count: int,
    ocr_md_path: str,
    chunks_path: str,
) -> AggregateResponse:
    """Aggregate chunk metadata into source_summary + source_insight.

    Raises ``ValueError`` if the LLM returns an unusable summary.
    """
    aggregate_input = json.dumps(
        {
            "chunk_metadata": chunk_metadata,
            "page_count": page_count,
            "ocr_model": "mistral-ocr-latest",
            "structuring_model": model,
            "extracted_markdown_path": ocr_md_path,
            "chunk_metadata_path": chunks_path,
        }
    )
    result = extract_structured(
        client=client,
        model=model,
        system_prompt=AGGREGATE_SYSTEM_PROMPT,
        user_content=aggregate_input,
        response_format=AggregateResponse,
        retries=1,
        name="pdf.aggregate",
        metadata={"stage": "pdf.aggregate", "page_count": page_count, "chunk_count": len(chunk_metadata)},
    )
    if not result.source_summary.summary.strip():
        raise ValueError("Aggregate extraction returned empty source_summary — unusable")
    return result


def extract_csv_content(client: OpenAIClient, model: str, profile_data: dict) -> CSVContentResponse:
    """Extract source_content for a CSV using structured extraction.

    Raises ``ValueError`` if the LLM returns no usable chunks or empty text.
    """
    result = extract_structured(
        client=client,
        model=model,
        system_prompt=CSV_CONTENT_SYSTEM_PROMPT,
        user_content=json.dumps(profile_data),
        response_format=CSVContentResponse,
        retries=1,
        name="csv.extract_content",
        metadata={"stage": "csv.extract_content"},
    )
    if not result.chunks:
        raise ValueError("CSV content extraction returned no chunks — unusable source_content")
    total_text = "".join(c.text for c in result.chunks).strip()
    if not total_text:
        raise ValueError("CSV content extraction returned chunks with no text — unusable source_content")
    return result


def extract_csv_insight(client: OpenAIClient, model: str, profile_data: dict) -> CSVInsightResponse:
    """Extract source_insight for a CSV using structured extraction."""
    return extract_structured(
        client=client,
        model=model,
        system_prompt=CSV_INSIGHT_SYSTEM_PROMPT,
        user_content=json.dumps(profile_data),
        response_format=CSVInsightResponse,
        retries=1,
        name="csv.extract_insight",
        metadata={"stage": "csv.extract_insight"},
    )
