"""Source data domain orchestration."""

import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.models.enums import CategoryLabel, ProcessingStatus, SourceFileType, TeamLabel
from app.models.source import SourceCategory, SourceData
from app.models.workspace import Workspace
from app.schemas.source import SourceCreate
from app.storage.local import save_upload

# Allowed file extensions
ALLOWED_EXTENSIONS = {"csv", "pdf"}


def _validate_file_extension(original_filename: str, file_type: SourceFileType) -> None:
    ext = Path(original_filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}")
    expected_ext = file_type.value
    if ext != expected_ext:
        raise ValueError(f"File extension '{ext}' does not match declared file type '{expected_ext}'")


def create_source(session: Session, data: SourceCreate, file_content: bytes) -> SourceData:
    """Create a Source record, save file to local storage, and enqueue processing."""
    _validate_file_extension(data.original_filename, data.file_type)
    if session.get(Workspace, data.workspace_id) is None:
        raise ValueError(f"Workspace {data.workspace_id} not found")

    # Create source record first to get ID for storage path
    source = SourceData(
        workspace_id=data.workspace_id,
        title=data.title,
        team_label=data.team_label,
        file_type=data.file_type,
        original_filename=data.original_filename,
        storage_path="",  # Will update after we have ID
        processing_status=ProcessingStatus.UPLOADED,
        period_start=data.period_start,
        period_end=data.period_end,
        period_label=data.period_label,
    )
    session.add(source)
    session.flush()  # Get ID without committing
    if source.id is None:
        raise RuntimeError("Source ID was not generated")

    source.storage_path = save_upload(data.workspace_id, source.id, data.original_filename, file_content)

    # Create category associations
    for cat in data.category_labels:
        category = SourceCategory(source_id=source.id, category=cat)
        session.add(category)

    session.commit()
    session.refresh(source)

    # Enqueue background processing
    _enqueue_processing(session, source)

    # Re-fetch to get updated status after async processing start
    session.refresh(source)
    return source


def _enqueue_processing(session: Session, source: SourceData) -> None:
    """Attempt to enqueue Celery task. Fall back to synchronous processing if unavailable."""
    from app.core.config import get_settings

    if not get_settings().rag_enable_background_processing:
        _process_source_sync(session, source)
        return

    # Try Celery first if celery_app is configured
    try:
        from app.jobs.celery_app import celery_app  # noqa: F401
        from app.jobs.source_processing import process_source_task

        # Attempt to send task - will raise if broker not available
        try:
            process_source_task.delay(source.id)
            return  # Successfully enqueued
        except Exception as celery_err:
            # Celery broker not available, fall through to sync
            import traceback
            traceback.print_exception(type(celery_err), celery_err, celery_err.__traceback__)
    except ImportError:
        pass  # Celery not installed, fall through to sync

    # Synchronous fallback: run processing directly in this thread
    # Safe for tests and environments without Redis/Celery
    _process_source_sync(session, source)


def _process_source_sync(session: Session, source: SourceData) -> None:
    """Run source processing synchronously."""
    if source.id is None:
        raise ValueError("Source must be persisted before processing")
    try:
        from app.services import source_processing
        source_processing.process_source(session, source.id)
    except Exception:
        # Already handled inside process_source with proper status set
        pass


def list_sources(
    session: Session,
    workspace_id: int,
    team_label: TeamLabel | None = None,
    category_label: CategoryLabel | None = None,
) -> list[SourceData]:
    """List non-deleted sources for a workspace, with optional filters."""
    query = select(SourceData).where(
        SourceData.workspace_id == workspace_id,
        SourceData.deleted_at.is_(None),
    )
    if team_label:
        query = query.where(SourceData.team_label == team_label)
    results = list(session.exec(query).all())

    if category_label:
        source_ids_with_cat = set(
            session.exec(
                select(SourceCategory.source_id).where(SourceCategory.category == category_label)
            ).all()
        )
        results = [s for s in results if s.id in source_ids_with_cat]

    return results


def get_source(session: Session, source_id: int) -> SourceData | None:
    """Get a source by ID (excludes soft-deleted)."""
    statement = select(SourceData).where(
        SourceData.id == source_id,
        SourceData.deleted_at.is_(None),
    )
    return session.exec(statement).first()


def get_source_for_audit(session: Session, source_id: int) -> SourceData | None:
    """Get a Source even if soft-deleted, for citation/audit checks."""
    return session.get(SourceData, source_id)


def soft_delete_source(session: Session, source_id: int) -> SourceData | None:
    """Soft-delete a source (sets deleted_at)."""
    source = session.get(SourceData, source_id)
    if not source:
        return None
    source.deleted_at = datetime.datetime.utcnow()
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def retry_processing(session: Session, source_id: int) -> SourceData:
    """Move a Failed source back toward Processing by re-enqueueing."""
    statement = select(SourceData).where(SourceData.id == source_id)
    source = session.exec(statement).first()
    if not source:
        raise ValueError(f"Source {source_id} not found")
    if source.deleted_at is not None:
        raise ValueError("Cannot retry processing for a deleted source")

    source.processing_status = ProcessingStatus.UPLOADED
    source.processing_error = None
    session.add(source)
    session.commit()
    session.refresh(source)

    _enqueue_processing(session, source)
    return source
