from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlmodel import Session

from app.db.session import get_session
from app.models.enums import CategoryLabel, SourceFileType, TeamLabel
from app.schemas.source import SourceCreate, SourceRead
from app.services import sources as source_service
from app.services.periods import derive_period_label

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(
    workspace_id: int = Form(..., description="Workspace ID from client-selected active workspace"),
    title: str = Form(...),
    team_label: TeamLabel = Form(...),
    category_labels: list[CategoryLabel] = Form(...),
    period_start_month: str = Form(...),
    period_end_month: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> SourceRead:
    """Upload a CSV or PDF source file and create Source metadata."""
    filename = file.filename or "upload"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        file_type = SourceFileType(extension)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV and PDF Sources are supported") from exc

    data = SourceCreate(
        workspace_id=workspace_id,
        title=title,
        team_label=team_label,
        category_labels=category_labels,
        file_type=file_type,
        original_filename=filename,
        period_start_month=period_start_month,
        period_end_month=period_end_month,
    )

    try:
        source = source_service.create_source(session, data, file.file.read())
    except ValueError as exc:
        detail = str(exc)
        validation_status = (
            status.HTTP_422_UNPROCESSABLE_ENTITY
            if "period_" in detail or "YYYY-MM" in detail
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=validation_status, detail=detail) from exc

    return _source_to_read(source, session)


@router.get("", response_model=list[SourceRead])
def list_sources(
    workspace_id: int = Query(..., description="Workspace ID from client-selected active workspace"),
    team_label: TeamLabel | None = Query(None),
    category_label: CategoryLabel | None = Query(None),
    session: Session = Depends(get_session),
) -> list[SourceRead]:
    """List sources for a workspace, scoped by workspace_id with optional filters."""
    sources = source_service.list_sources(session, workspace_id, team_label, category_label)
    return [_source_to_read(s, session) for s in sources]


@router.get("/{source_id}", response_model=SourceRead)
def get_source(
    source_id: int,
    session: Session = Depends(get_session),
) -> SourceRead:
    """Get a source by ID."""
    source = source_service.get_source(session, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return _source_to_read(source, session)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: int,
    session: Session = Depends(get_session),
) -> None:
    """Soft-delete a source (sets deleted_at)."""
    source = source_service.soft_delete_source(session, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")


@router.post("/{source_id}/retry-processing", response_model=SourceRead)
def retry_processing(
    source_id: int,
    session: Session = Depends(get_session),
) -> SourceRead:
    """Retry processing for a Failed source."""
    try:
        source = source_service.retry_processing(session, source_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _source_to_read(source, session)


def _source_to_read(source, session: Session) -> SourceRead:
    """Convert SourceData model to SourceRead schema with category_labels."""
    from sqlmodel import select

    from app.models.source import SourceCategory

    cat_labels = list(
        session.exec(select(SourceCategory.category).where(SourceCategory.source_id == source.id)).all()
    )
    return SourceRead(
        id=source.id,
        workspace_id=source.workspace_id,
        title=source.title,
        team_label=source.team_label,
        category_labels=cat_labels,
        file_type=source.file_type,
        processing_status=source.processing_status,
        processing_error=source.processing_error,
        original_filename=source.original_filename,
        storage_path=source.storage_path,
        period_start_month=source.period_start_month,
        period_end_month=source.period_end_month,
        period_label=derive_period_label(source.period_start_month, source.period_end_month),
        uploaded_at=source.uploaded_at,
        processed_at=source.processed_at,
        deleted_at=source.deleted_at,
    )
