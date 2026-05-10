"""Visualization artifact query orchestration."""

from datetime import datetime

from sqlmodel import Session, select

from app.models.enums import CategoryLabel, TeamLabel
from app.models.source import SourceArtifact, SourceCategory, SourceData
from app.schemas.visualization import VisualizationArtifactRead


def list_visualizations(
    session: Session,
    workspace_id: int,
    team_label: TeamLabel | None = None,
    category_label: CategoryLabel | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> list[VisualizationArtifactRead]:
    """List visualization artifacts for ready sources in a workspace with optional filters.

    Only returns artifacts from sources with processing_status == Ready.
    Excludes soft-deleted sources.
    """
    # Build source query with filters
    source_query = select(SourceData).where(
        SourceData.workspace_id == workspace_id,
        SourceData.deleted_at.is_(None),
        SourceData.processing_status == "ready",
    )
    if team_label:
        source_query = source_query.where(SourceData.team_label == team_label)
    if period_start is not None:
        source_query = source_query.where(SourceData.period_start >= period_start)
    if period_end is not None:
        source_query = source_query.where(SourceData.period_end <= period_end)

    sources = list(session.exec(source_query).all())

    # Filter by category if specified
    if category_label:
        source_ids_with_cat = set(
            session.exec(
                select(SourceCategory.source_id).where(SourceCategory.category == category_label)
            ).all()
        )
        sources = [s for s in sources if s.id in source_ids_with_cat]

    # Collect artifacts for each source, including source metadata
    results: list[VisualizationArtifactRead] = []
    for source in sources:
        cat_labels = list(
            session.exec(
                select(SourceCategory.category).where(SourceCategory.source_id == source.id)
            ).all()
        )
        artifacts = session.exec(
            select(SourceArtifact).where(SourceArtifact.source_id == source.id)
        ).all()
        for art in artifacts:
            results.append(VisualizationArtifactRead(
                id=art.id,
                source_id=art.source_id,
                artifact_type=art.artifact_type,
                title=art.title,
                content_json=art.content_json,
                source_title=source.title,
                source_file_type=source.file_type,
                team_label=source.team_label,
                category_labels=cat_labels,
            ))

    return results


def get_visualization_for_source(
    session: Session,
    source_id: int,
) -> list[VisualizationArtifactRead]:
    """Get all visualization artifacts for a specific source.

    Returns empty list if source is not found, deleted, or not ready.
    """
    source = session.get(SourceData, source_id)
    if not source or source.deleted_at or source.processing_status != "ready":
        return []

    cat_labels = list(
        session.exec(
            select(SourceCategory.category).where(SourceCategory.source_id == source_id)
        ).all()
    )
    artifacts = session.exec(
        select(SourceArtifact).where(SourceArtifact.source_id == source_id)
    ).all()
    return [
        VisualizationArtifactRead(
            id=art.id,
            source_id=art.source_id,
            artifact_type=art.artifact_type,
            title=art.title,
            content_json=art.content_json,
            source_title=source.title,
            source_file_type=source.file_type,
            team_label=source.team_label,
            category_labels=cat_labels,
        )
        for art in artifacts
    ]
