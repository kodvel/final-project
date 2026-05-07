from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.session import get_session
from app.models.enums import CategoryLabel, TeamLabel
from app.schemas.visualization import VisualizationArtifactRead
from app.services import visualizations as viz_service

router = APIRouter(prefix="/visualizations", tags=["visualizations"])


@router.get("", response_model=list[VisualizationArtifactRead])
def list_visualizations(
    workspace_id: int = Query(..., description="Workspace ID from client-selected active workspace"),
    team_label: TeamLabel | None = Query(None),
    category_label: CategoryLabel | None = Query(None),
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    session: Session = Depends(get_session),
) -> list[VisualizationArtifactRead]:
    """List visualization artifacts for ready sources in a workspace with optional filters.

    Returns csv_profile, chart_spec, and insight_card artifacts from processed CSV sources.
    """
    return viz_service.list_visualizations(
        session=session,
        workspace_id=workspace_id,
        team_label=team_label,
        category_label=category_label,
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/{source_id}", response_model=list[VisualizationArtifactRead])
def get_visualization_for_source(
    source_id: int,
    session: Session = Depends(get_session),
) -> list[VisualizationArtifactRead]:
    """Get all visualization artifacts for a specific source."""
    return viz_service.get_visualization_for_source(session=session, source_id=source_id)