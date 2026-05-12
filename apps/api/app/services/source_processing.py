"""Testable source-processing orchestration shared by jobs and routes."""

import traceback
from datetime import datetime
from pathlib import Path

from sqlmodel import Session

from app.models.enums import ArtifactType, ProcessingStatus, SourceFileType
from app.models.source import SourceData
from app.services import csv_profiler
from app.services.artifacts import (
    list_source_artifacts,
    replace_source_artifacts,
)


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

    except Exception as exc:
        source.processing_status = ProcessingStatus.FAILED
        source.processing_error = f"{type(exc).__name__}: {exc}"
        session.add(source)
        session.commit()
        traceback.print_exc()

    session.refresh(source)
    return source


def _process_pdf(session: Session, source: SourceData) -> None:
    """Process a PDF source through the full pipeline."""
    from app.services.pdf_extractor import process_pdf

    process_pdf(session, source)


def _process_csv(session: Session, source: SourceData) -> None:
    """Profile a CSV source and generate source_summary, source_content, source_insight artifacts."""
    storage_path = Path(source.storage_path)
    if not storage_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {storage_path}")

    # Profile the CSV
    profile = csv_profiler.profile_csv_from_path(storage_path)

    # Build new artifact set
    new_artifacts: list[SourceArtifact] = []

    # 1. source_summary artifact (required) — dataset overview
    from app.models.source import SourceArtifact  # local import to keep top-level clean

    summary_data = csv_profiler.build_source_summary(profile)
    new_artifacts.append(SourceArtifact(
        source_id=source.id,
        artifact_type=ArtifactType.SOURCE_SUMMARY,
        title=f"Summary: {source.title}",
        content_json=summary_data,
    ))

    # 2. source_content artifact — column-level profiling data
    content_data = csv_profiler.build_source_content(profile)
    new_artifacts.append(SourceArtifact(
        source_id=source.id,
        artifact_type=ArtifactType.SOURCE_CONTENT,
        title=f"Content: {source.title}",
        content_json=content_data,
    ))

    # 3. source_insight artifact — statistical insights (optional)
    insight_data = csv_profiler.build_source_insight(profile)
    if insight_data.get("findings") or insight_data.get("risks"):
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
