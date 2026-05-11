"""Testable source-processing orchestration shared by jobs and routes."""

import traceback
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.models.enums import ProcessingStatus, SourceFileType
from app.models.source import SourceArtifact, SourceData
from app.services import csv_profiler


def process_source(session: Session, source_id: int) -> SourceData:
    """Process a source file and generate visualization artifacts.

    - For CSV: profile, generate chart specs and insight cards.
    - For PDF: OCR, chunk, label, aggregate into source_summary and source_insight.

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
        if source.file_type == SourceFileType.CSV:
            _process_csv(session, source)
        elif source.file_type == SourceFileType.PDF:
            _process_pdf(session, source)
        else:
            raise ValueError(f"Unsupported file type: {source.file_type}")

        # Ensure we have at least one artifact before marking Ready
        artifacts = _get_artifacts_for_source(session, source_id)
        if source.file_type == SourceFileType.CSV and not artifacts:
            raise ValueError("No artifacts generated during CSV processing")
        if artifacts:
            source.processing_status = ProcessingStatus.READY
            source.processed_at = datetime.utcnow()
            source.processing_error = None
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

    # Mark ready if artifacts were generated
    artifacts = _get_artifacts_for_source(session, source.id)
    if artifacts:
        source.processing_status = ProcessingStatus.READY
        source.processed_at = datetime.utcnow()
        source.processing_error = None
        session.add(source)
        session.commit()


def _process_csv(session: Session, source: SourceData) -> None:
    """Profile a CSV source and generate all artifact types."""
    storage_path = Path(source.storage_path)
    if not storage_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {storage_path}")

    # Delete existing CSV artifacts for this source (replace behavior)
    existing = session.exec(
        select(SourceArtifact).where(SourceArtifact.source_id == source.id)
    ).all()
    for art in existing:
        session.delete(art)
    session.commit()

    # Profile the CSV
    profile = csv_profiler.profile_csv_from_path(storage_path)

    # 1. csv_profile artifact (required)
    profile_artifact = SourceArtifact(
        source_id=source.id,
        artifact_type="csv_profile",
        title=f"Profile: {source.title}",
        content_json=profile.to_dict(),
    )
    session.add(profile_artifact)

    # 2. chart_spec artifacts when useful inputs exist
    chart_specs = csv_profiler.build_chart_spec(profile)
    for spec in chart_specs:
        chart_artifact = SourceArtifact(
            source_id=source.id,
            artifact_type="chart_spec",
            title=spec.get("display_title", spec.get("title", "Chart")),
            content_json=spec,
        )
        session.add(chart_artifact)

    # 3. insight_card artifacts when identifiable insights exist
    insight_cards = csv_profiler.build_insight_card(profile)
    for insight in insight_cards:
        insight_artifact = SourceArtifact(
            source_id=source.id,
            artifact_type="insight_card",
            title=insight.get("title", "Insight"),
            content_json=insight,
        )
        session.add(insight_artifact)

    session.commit()


def _get_artifacts_for_source(session: Session, source_id: int) -> list[SourceArtifact]:
    """Fetch all artifacts for a source."""
    return list(session.exec(select(SourceArtifact).where(SourceArtifact.source_id == source_id)).all())


def get_artifacts_by_source(session: Session, source_id: int) -> list[SourceArtifact]:
    """Public interface: get all artifacts for a source (excludes soft-deleted sources)."""
    return _get_artifacts_for_source(session, source_id)
