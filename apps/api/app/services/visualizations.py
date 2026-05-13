"""Visualization Snapshot composer — period-based cached intelligence."""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlmodel import Session, select

from app.models.source import SourceArtifact, SourceData
from app.models.visualization_snapshot import VisualizationSnapshot
from app.schemas.visualization import VisualizationSnapshotRead
from app.services.periods import (
    derive_period_label,
    ranges_overlap,
    validate_month,
    validate_period_range,
)


def _scope_hash(workspace_id: int, period_start_month: str, period_end_month: str) -> str:
    raw = f"{workspace_id}:{period_start_month}:{period_end_month}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _find_cached(session: Session, workspace_id: int, period_start_month: str, period_end_month: str) -> VisualizationSnapshot | None:
    stmt = select(VisualizationSnapshot).where(
        VisualizationSnapshot.workspace_id == workspace_id,
        VisualizationSnapshot.period_start_month == period_start_month,
        VisualizationSnapshot.period_end_month == period_end_month,
        VisualizationSnapshot.status == "ready",
    )
    return session.exec(stmt).first()


def _query_overlapping_sources(
    session: Session,
    workspace_id: int,
    period_start_month: str,
    period_end_month: str,
) -> list[SourceData]:
    """Return ready, non-deleted sources in workspace overlapping the requested period."""
    stmt = select(SourceData).where(
        SourceData.workspace_id == workspace_id,
        SourceData.deleted_at.is_(None),
        SourceData.processing_status == "ready",
    )
    candidates = list(session.exec(stmt).all())
    return [
        s for s in candidates
        if ranges_overlap(
            s.period_start_month, s.period_end_month,
            period_start_month, period_end_month,
        )
    ]


def _collect_artifacts(session: Session, source_ids: list[int]) -> list[SourceArtifact]:
    if not source_ids:
        return []
    stmt = select(SourceArtifact).where(SourceArtifact.source_id.in_(source_ids))
    return list(session.exec(stmt).all())


def _compose_content(
    sources: list[SourceData],
    artifacts: list[SourceArtifact],
    period_label: str | None,
) -> dict:
    """Compose content_json sections from sources and artifacts."""
    summaries: list[dict] = []
    insights: list[dict] = []
    content_chunks: list[dict] = []

    for art in artifacts:
        entry = {
            "source_id": art.source_id,
            "artifact_id": art.id,
            "title": art.title,
            "data": art.content_json,
        }
        if art.artifact_type == "source_summary":
            summaries.append(entry)
        elif art.artifact_type == "source_insight":
            insights.append(entry)
        elif art.artifact_type == "source_content":
            content_chunks.append(entry)

    source_cards = []
    for src in sources:
        card = {
            "source_id": src.id,
            "title": src.title,
            "team_label": src.team_label,
            "file_type": src.file_type,
            "period_start_month": src.period_start_month,
            "period_end_month": src.period_end_month,
        }
        source_cards.append(card)

    # Extract findings from insights
    key_findings: list[dict] = []
    for ins in insights:
        for finding in ins.get("data", {}).get("findings", []):
            key_findings.append({
                "text": finding.get("text", ""),
                "evidence": {
                    "source_id": ins["source_id"],
                    "artifact_id": ins["artifact_id"],
                },
            })

    coverage = {
        "total_sources": len(sources),
        "period_label": period_label,
        "sources": source_cards,
    }

    # Gather unique source IDs that have summaries/insights for completeness tracking
    covered_ids = {art.source_id for art in artifacts if art.artifact_type in ("source_summary", "source_insight")}
    gaps: list[str] = []
    if len(sources) == 0:
        gaps.append("No ready sources overlap the requested period.")
    for src in sources:
        if src.id not in covered_ids:
            gaps.append(f"Source '{src.title}' (id={src.id}) has no summary or insight artifacts.")

    return {
        "coverage": coverage,
        "source_cards": source_cards,
        "key_findings": key_findings,
        "risks_assumptions": [],
        "opportunities": [],
        "gaps": gaps,
    }


def _snapshot_to_read(snapshot: VisualizationSnapshot) -> VisualizationSnapshotRead:
    return VisualizationSnapshotRead(
        id=snapshot.id,
        workspace_id=snapshot.workspace_id,
        period_start_month=snapshot.period_start_month,
        period_end_month=snapshot.period_end_month,
        title=snapshot.title,
        content_json=snapshot.content_json,
        source_ids_json=snapshot.source_ids_json,
        artifact_ids_json=snapshot.artifact_ids_json,
        status=snapshot.status,
        generation_error=snapshot.generation_error,
        generated_at=snapshot.generated_at,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
    )


def get_visualization_snapshot(
    session: Session,
    workspace_id: int,
    period_start_month: str,
    period_end_month: str,
) -> VisualizationSnapshotRead:
    """Return cached snapshot if present, otherwise compose and save a new one."""
    period_start_month = validate_month(period_start_month, "period_start_month")
    period_end_month = validate_month(period_end_month, "period_end_month")
    validate_period_range(period_start_month, period_end_month)

    cached = _find_cached(session, workspace_id, period_start_month, period_end_month)
    if cached is not None:
        return _snapshot_to_read(cached)

    return _compose_and_save(session, workspace_id, period_start_month, period_end_month)


def refresh_visualization_snapshot(
    session: Session,
    workspace_id: int,
    period_start_month: str,
    period_end_month: str,
) -> VisualizationSnapshotRead:
    """Force regeneration of snapshot for the given scope."""
    period_start_month = validate_month(period_start_month, "period_start_month")
    period_end_month = validate_month(period_end_month, "period_end_month")
    validate_period_range(period_start_month, period_end_month)

    # Delete existing snapshot(s) for this scope
    existing = _find_cached(session, workspace_id, period_start_month, period_end_month)
    if existing is not None:
        session.delete(existing)
        session.flush()

    return _compose_and_save(session, workspace_id, period_start_month, period_end_month)


def _compose_and_save(
    session: Session,
    workspace_id: int,
    period_start_month: str,
    period_end_month: str,
) -> VisualizationSnapshotRead:
    """Compose snapshot content, persist it, and return the read schema."""
    sources = _query_overlapping_sources(session, workspace_id, period_start_month, period_end_month)
    source_ids = [s.id for s in sources]

    artifacts = _collect_artifacts(session, source_ids)
    artifact_ids = [a.id for a in artifacts]

    period_label = derive_period_label(period_start_month, period_end_month)
    title = f"Visualization: {period_label or f'{period_start_month} – {period_end_month}'}"
    content = _compose_content(sources, artifacts, period_label)

    now = datetime.utcnow()
    snapshot = VisualizationSnapshot(
        workspace_id=workspace_id,
        period_start_month=period_start_month,
        period_end_month=period_end_month,
        scope_hash=_scope_hash(workspace_id, period_start_month, period_end_month),
        title=title,
        content_json=content,
        source_ids_json=source_ids,
        artifact_ids_json=artifact_ids,
        status="ready",
        generated_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return _snapshot_to_read(snapshot)


# ---------------------------------------------------------------------------
# Legacy helpers kept for backward compatibility with artifact-level tests
# ---------------------------------------------------------------------------

def list_visualizations(
    session: Session,
    workspace_id: int,
    team_label=None,
    category_label=None,
    period_start_month: str | None = None,
    period_end_month: str | None = None,
):
    """Legacy: list visualization artifacts per source. Tests use /visualizations/{source_id}."""
    from app.models.source import SourceCategory
    from app.schemas.visualization import VisualizationArtifactRead

    source_query = select(SourceData).where(
        SourceData.workspace_id == workspace_id,
        SourceData.deleted_at.is_(None),
        SourceData.processing_status == "ready",
    )
    if team_label:
        source_query = source_query.where(SourceData.team_label == team_label)

    sources = list(session.exec(source_query).all())

    if period_start_month is not None or period_end_month is not None:
        sources = [
            s for s in sources
            if ranges_overlap(
                s.period_start_month, s.period_end_month,
                period_start_month, period_end_month,
            )
        ]

    if category_label:
        source_ids_with_cat = set(
            session.exec(
                select(SourceCategory.source_id).where(SourceCategory.category == category_label)
            ).all()
        )
        sources = [s for s in sources if s.id in source_ids_with_cat]

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


def get_visualization_for_source(session: Session, source_id: int):
    """Legacy: get artifacts for a single source."""
    from app.models.source import SourceCategory
    from app.schemas.visualization import VisualizationArtifactRead

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
