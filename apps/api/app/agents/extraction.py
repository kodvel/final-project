"""Shared LLM extraction service using OpenAI structured parsing.

Replaces manual LiteLLM calls and JSON repair logic with
``client.chat.completions.parse(..., response_format=PydanticModel)``.

All extraction functions accept an *OpenAI client instance* so that callers
control client lifecycle and tests can inject mocks without touching settings.
"""

import json
import logging
from typing import Any, TypeVar

from openai import OpenAI as OpenAIClient
from pydantic import BaseModel, Field

from app.agents.prompt_registry import load_prompt
from app.agents.prompts import (
    AGGREGATE_SYSTEM_PROMPT,
    CHUNK_LABEL_SYSTEM_PROMPT,
    CSV_CONTENT_SYSTEM_PROMPT,
    CSV_INSIGHT_SYSTEM_PROMPT,
    VISUALIZATION_SNAPSHOT_SYSTEM_PROMPT,
)

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
    langfuse_prompt: Any | None = None,
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
        langfuse_prompt: Optional Langfuse prompt object to link with the
            generation (so the UI shows which prompt version produced this
            output). Forwarded only when the langfuse OpenAI wrapper is used.

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
    if langfuse_prompt is not None:
        extra_kwargs["langfuse_prompt"] = langfuse_prompt
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


# --- Visualization Snapshot composition ---


class VisualizationEvidenceRef(BaseModel):
    """Evidence reference for a cross-artifact visualization claim."""

    source_id: int
    artifact_id: int
    source_title: str | None = None


class VisualizationInsightItem(BaseModel):
    """One board-ready insight grounded in one or more Source Artifacts."""

    text: str
    confidence: str = "medium"
    evidence: list[VisualizationEvidenceRef] = Field(default_factory=list)
    theme: str | None = None
    kind: str | None = None


class VisualizationSnapshotExtract(BaseModel):
    """Structured LLM output for cross-artifact Visualization Snapshot composition."""

    executive_summary: str = ""
    key_findings: list[VisualizationInsightItem] = Field(default_factory=list)
    risks_assumptions: list[VisualizationInsightItem] = Field(default_factory=list)
    opportunities: list[VisualizationInsightItem] = Field(default_factory=list)
    cross_source_patterns: list[VisualizationInsightItem] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    confidence_assessment: str = "medium"


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
    metadata: dict = {"stage": "pdf.label_chunk"}
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index
    prompt = load_prompt("pdf-chunk-label-system", CHUNK_LABEL_SYSTEM_PROMPT)
    return extract_structured(
        client=client,
        model=model,
        system_prompt=prompt.text,
        user_content=chunk_text,
        response_format=ChunkLabelResponse,
        retries=1,
        name="pdf.label_chunk",
        metadata=metadata,
        langfuse_prompt=prompt.langfuse_prompt,
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
    prompt = load_prompt("pdf-aggregate-system", AGGREGATE_SYSTEM_PROMPT)
    result = extract_structured(
        client=client,
        model=model,
        system_prompt=prompt.text,
        user_content=aggregate_input,
        response_format=AggregateResponse,
        retries=1,
        name="pdf.aggregate",
        metadata={"stage": "pdf.aggregate", "page_count": page_count, "chunk_count": len(chunk_metadata)},
        langfuse_prompt=prompt.langfuse_prompt,
    )
    if not result.source_summary.summary.strip():
        raise ValueError("Aggregate extraction returned empty source_summary — unusable")
    return result


def extract_csv_content(client: OpenAIClient, model: str, profile_data: dict) -> CSVContentResponse:
    """Extract source_content for a CSV using structured extraction.

    Raises ``ValueError`` if the LLM returns no usable chunks or empty text.
    """
    prompt = load_prompt("csv-content-system", CSV_CONTENT_SYSTEM_PROMPT)
    result = extract_structured(
        client=client,
        model=model,
        system_prompt=prompt.text,
        user_content=json.dumps(profile_data),
        response_format=CSVContentResponse,
        retries=1,
        name="csv.extract_content",
        metadata={"stage": "csv.extract_content"},
        langfuse_prompt=prompt.langfuse_prompt,
    )
    if not result.chunks:
        raise ValueError("CSV content extraction returned no chunks — unusable source_content")
    total_text = "".join(c.text for c in result.chunks).strip()
    if not total_text:
        raise ValueError("CSV content extraction returned chunks with no text — unusable source_content")
    return result


def extract_csv_insight(client: OpenAIClient, model: str, profile_data: dict) -> CSVInsightResponse:
    """Extract source_insight for a CSV using structured extraction."""
    prompt = load_prompt("csv-insight-system", CSV_INSIGHT_SYSTEM_PROMPT)
    return extract_structured(
        client=client,
        model=model,
        system_prompt=prompt.text,
        user_content=json.dumps(profile_data),
        response_format=CSVInsightResponse,
        retries=1,
        name="csv.extract_insight",
        metadata={"stage": "csv.extract_insight"},
        langfuse_prompt=prompt.langfuse_prompt,
    )


def extract_visualization_snapshot(
    client: OpenAIClient,
    model: str,
    artifact_payload: dict,
) -> VisualizationSnapshotExtract:
    """Compose a cross-artifact Visualization Snapshot using structured extraction."""
    prompt = load_prompt("visualization-snapshot-system", VISUALIZATION_SNAPSHOT_SYSTEM_PROMPT)
    result = extract_structured(
        client=client,
        model=model,
        system_prompt=prompt.text,
        user_content=json.dumps(artifact_payload, ensure_ascii=False),
        response_format=VisualizationSnapshotExtract,
        temperature=0.2,
        retries=1,
        name="visualization.compose_snapshot",
        metadata={
            "stage": "visualization.compose_snapshot",
            "source_count": len(artifact_payload.get("sources", [])),
            "period_label": artifact_payload.get("period", {}).get("label"),
        },
        langfuse_prompt=prompt.langfuse_prompt,
    )
    claim_groups = [
        *result.key_findings,
        *result.risks_assumptions,
        *result.opportunities,
        *result.cross_source_patterns,
    ]
    has_usable_output = bool(result.executive_summary.strip()) and bool(claim_groups)
    if not has_usable_output:
        raise ValueError("Visualization snapshot extraction returned no usable cross-source output")
    uncited = [item.text for item in claim_groups if not item.evidence]
    if uncited:
        raise ValueError("Visualization snapshot extraction returned uncited claims")
    return result
