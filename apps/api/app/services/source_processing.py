"""Testable source-processing orchestration shared by jobs and routes."""

import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from openai import OpenAI as OpenAIClient
from sqlmodel import Session

from app.core.config import get_settings
from app.models.enums import ArtifactType, ProcessingStatus, SourceFileType
from app.models.source import SourceData
from app.services import csv_profiler, llm_extraction
from app.services.artifacts import (
    list_source_artifacts,
    replace_source_artifacts,
)


@contextmanager
def _langfuse_source_span(source: SourceData):
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        yield None
        return

    from langfuse import get_client, propagate_attributes

    langfuse = get_client()
    metadata = {
        "workspaceId": str(source.workspace_id),
        "sourceId": str(source.id or ""),
        "fileType": str(source.file_type),
        "sourceTitle": source.title,
    }
    # Workspace is the multi-tenant principal — set as user_id so the Users
    # view in Langfuse aggregates per workspace, matching the chat trace setup.
    with propagate_attributes(
        user_id=f"workspace:{source.workspace_id}",
        tags=["source-processing", str(source.file_type), f"workspace:{source.workspace_id}"],
        metadata=metadata,
    ):
        with langfuse.start_as_current_observation(
            name=f"source.process:{source.file_type}",
            as_type="span",
            input={
                "source_id": source.id,
                "file_type": str(source.file_type),
                "title": source.title,
            },
        ) as span:
            yield span


def _update_langfuse_span(span, status: str, error: str | None = None) -> None:
    if not span:
        return
    payload: dict[str, str] = {"status": status}
    if error:
        payload["error"] = error
    span.update(output=payload)


def process_source(session: Session, source_id: int) -> SourceData:
    """Process a source file and generate Source Artifacts.

    - For CSV: profile → source_summary, source_content, source_insight.
    - For PDF: OCR, chunk, label, aggregate → source_summary, source_content, source_insight.

    Sets processing_status to Processing -> Ready (or Failed on error).
    """
    source = session.get(SourceData, source_id)
    if not source:
        raise ValueError(f"Source {source_id} not found")

    # Set status to Processing
    source.processing_status = ProcessingStatus.PROCESSING
    source.processing_error = None
    session.add(source)
    session.commit()
    session.refresh(source)

    with _langfuse_source_span(source) as span:
        try:
            # Delete old ChromaDB vectors before reprocessing
            from app.knowledge.indexing import delete_source_vectors

            delete_source_vectors(source_id)

            if source.file_type == SourceFileType.CSV:
                _process_csv(session, source)
            elif source.file_type == SourceFileType.PDF:
                _process_pdf(session, source)
            else:
                raise ValueError(f"Unsupported file type: {source.file_type}")

            # Require both source_summary and source_content for Ready status
            artifacts = list_source_artifacts(session, source_id)
            artifact_types = {a.artifact_type for a in artifacts}
            required = {str(ArtifactType.SOURCE_SUMMARY), str(ArtifactType.SOURCE_CONTENT)}
            if required.issubset(artifact_types):
                # Index source_content chunks into ChromaDB before marking Ready
                from app.knowledge.indexing import index_source_content

                index_source_content(session, source_id)

                source.processing_status = ProcessingStatus.READY
                source.processed_at = datetime.utcnow()
                source.processing_error = None
            else:
                missing = required - artifact_types
                raise ValueError(f"Missing required artifacts for Ready: {missing}")
            session.add(source)
            session.commit()
            _update_langfuse_span(span, "completed")

        except Exception as exc:
            source.processing_status = ProcessingStatus.FAILED
            source.processing_error = f"{type(exc).__name__}: {exc}"
            session.add(source)
            session.commit()
            _update_langfuse_span(span, "failed", source.processing_error)
            traceback.print_exc()

    session.refresh(source)
    return source


def _process_pdf(session: Session, source: SourceData) -> None:
    """Process a PDF source through the full pipeline."""
    from app.services.pdf_extractor import process_pdf

    process_pdf(session, source)


def _process_csv(session: Session, source: SourceData) -> None:
    """Profile a CSV source and generate source_summary, source_content, source_insight artifacts.

    * ``source_summary`` is deterministic (via ``csv_profiler.build_source_summary``).
    * ``source_content`` and ``source_insight`` are LLM-generated using compact profile data.
    * If LLM extraction fails the exception bubbles up to ``process_source`` → status Failed.
    """
    from app.core.config import get_settings
    from app.models.source import SourceArtifact  # local import to keep top-level clean

    storage_path = Path(source.storage_path)
    if not storage_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {storage_path}")
    if source.id is None:
        raise ValueError("Source must be persisted before CSV processing")

    # Profile the CSV deterministically
    profile = csv_profiler.profile_csv_from_path(storage_path)

    # Create OpenAI client from RAG settings — if key is missing this raises,
    # which bubbles up to process_source and marks the source as Failed.
    settings = get_settings()
    from app.services.langfuse_openai import create_openai_client

    client = create_openai_client(
        api_key=settings.rag_openai_api_key,
        base_url=settings.rag_openai_api_base_url,
    )
    model = settings.rag_openai_model

    # Compact profile data for LLM (no raw rows, no file_path)
    profile_data = csv_profiler.build_csv_llm_profile(profile)

    new_artifacts: list[SourceArtifact] = []

    # 1. source_summary artifact (required) — deterministic
    summary_data = csv_profiler.build_source_summary(profile)
    new_artifacts.append(SourceArtifact(
        source_id=source.id,
        artifact_type=ArtifactType.SOURCE_SUMMARY,
        title=f"Summary: {source.title}",
        content_json=summary_data,
    ))

    # 2. source_content artifact — LLM-generated
    content_response = llm_extraction.extract_csv_content(client, model, profile_data)
    new_artifacts.append(SourceArtifact(
        source_id=source.id,
        artifact_type=ArtifactType.SOURCE_CONTENT,
        title=f"Content: {source.title}",
        content_json=content_response.model_dump(),
    ))

    # 3. source_insight artifact — LLM-generated (optional — only if useful)
    insight_response = llm_extraction.extract_csv_insight(client, model, profile_data)
    insight_data = insight_response.model_dump()
    if insight_data.get("findings") or insight_data.get("risks") or insight_data.get("opportunities") or insight_data.get("assumptions") or insight_data.get("warnings"):
        new_artifacts.append(SourceArtifact(
            source_id=source.id,
            artifact_type=ArtifactType.SOURCE_INSIGHT,
            title=f"Insight: {source.title}",
            content_json=insight_data,
        ))

    # Replace all existing artifacts for this source
    replace_source_artifacts(session, source.id, new_artifacts)
    session.commit()


def get_artifacts_by_source(session: Session, source_id: int) -> list:
    """Public interface: get all artifacts for a source (excludes soft-deleted sources)."""
    return list_source_artifacts(session, source_id)
