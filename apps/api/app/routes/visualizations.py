from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.visualization import VisualizationArtifactRead, VisualizationSnapshotRead
from app.services import visualizations as viz_service

router = APIRouter(prefix="/visualizations", tags=["visualizations"])


class RefreshRequest(BaseModel):
    workspace_id: int
    period_start_month: str
    period_end_month: str


@router.get("", response_model=VisualizationSnapshotRead)
def get_visualization_snapshot(
    workspace_id: int = Query(..., description="Workspace ID"),
    period_start_month: str = Query(..., description="Start month YYYY-MM"),
    period_end_month: str = Query(..., description="End month YYYY-MM"),
    session: Session = Depends(get_session),
) -> VisualizationSnapshotRead:
    """Get (or compose on first request) the Visualization Snapshot for a workspace and period."""
    return viz_service.get_visualization_snapshot(
        session=session,
        workspace_id=workspace_id,
        period_start_month=period_start_month,
        period_end_month=period_end_month,
    )


@router.post("/refresh", response_model=VisualizationSnapshotRead)
def refresh_visualization_snapshot(
    body: RefreshRequest,
    session: Session = Depends(get_session),
) -> VisualizationSnapshotRead:
    """Force regeneration of the Visualization Snapshot for a workspace and period."""
    return viz_service.refresh_visualization_snapshot(
        session=session,
        workspace_id=body.workspace_id,
        period_start_month=body.period_start_month,
        period_end_month=body.period_end_month,
    )


# ---------------------------------------------------------------------------
# Legacy per-source artifact endpoint (kept for existing CSV processing tests)
# ---------------------------------------------------------------------------

@router.get("/source/{source_id}", response_model=list[VisualizationArtifactRead])
def get_visualization_for_source(
    source_id: int,
    session: Session = Depends(get_session),
) -> list[VisualizationArtifactRead]:
    """Get all visualization artifacts for a specific source (legacy, new path)."""
    return viz_service.get_visualization_for_source(session=session, source_id=source_id)


@router.get("/{source_id}", response_model=list[VisualizationArtifactRead])
def get_visualization_for_source_legacy(
    source_id: int,
    session: Session = Depends(get_session),
) -> list[VisualizationArtifactRead]:
    """Get all visualization artifacts for a specific source (legacy, old path)."""
    return viz_service.get_visualization_for_source(session=session, source_id=source_id)
