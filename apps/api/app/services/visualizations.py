"""Visualization Snapshot composer — period-based cached intelligence."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.source import SourceArtifact, SourceCategory, SourceData
from app.models.visualization_snapshot import VisualizationSnapshot
from app.schemas.visualization import VisualizationSnapshotRead
from app.services.langfuse_openai import create_openai_client
from app.services.llm_extraction import extract_visualization_snapshot
from app.services.periods import (
    derive_period_label,
    ranges_overlap,
    validate_month,
    validate_period_range,
)

logger = logging.getLogger(__name__)


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


def _category_labels_by_source(session: Session, source_ids: list[int]) -> dict[int, list[str]]:
    if not source_ids:
        return {}
    rows = session.exec(
        select(SourceCategory).where(SourceCategory.source_id.in_(source_ids))
    ).all()
    labels: dict[int, list[str]] = {source_id: [] for source_id in source_ids}
    for row in rows:
        labels.setdefault(row.source_id, []).append(_plain_value(row.category))
    return labels


def _plain_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _artifact_data(artifact: SourceArtifact | None) -> dict:
    if artifact is None or not isinstance(artifact.content_json, dict):
        return {}
    return artifact.content_json


def _latest_artifact(artifacts: list[SourceArtifact]) -> SourceArtifact | None:
    if not artifacts:
        return None
    return sorted(artifacts, key=lambda art: (art.updated_at, art.id or 0), reverse=True)[0]


def _group_artifacts(artifacts: list[SourceArtifact]) -> dict[int, dict[str, list[SourceArtifact]]]:
    grouped: dict[int, dict[str, list[SourceArtifact]]] = {}
    for artifact in artifacts:
        by_type = grouped.setdefault(artifact.source_id, {})
        by_type.setdefault(artifact.artifact_type, []).append(artifact)
    return grouped


def _compute_fingerprint(sources: list[SourceData], artifacts: list[SourceArtifact], categories: dict[int, list[str]]) -> str:
    parts: list[str] = []
    for source in sorted(sources, key=lambda item: item.id or 0):
        source_id = source.id or 0
        parts.append(
            ":".join(
                [
                    "source",
                    str(source_id),
                    _plain_value(source.processing_status),
                    source.period_start_month,
                    source.period_end_month,
                    _plain_value(source.team_label),
                    _plain_value(source.file_type),
                    source.updated_at.isoformat(),
                    ",".join(sorted(categories.get(source_id, []))),
                ]
            )
        )
    for artifact in sorted(artifacts, key=lambda item: (item.source_id, item.artifact_type, item.id or 0)):
        parts.append(
            ":".join(
                [
                    "artifact",
                    str(artifact.source_id),
                    str(artifact.id or 0),
                    artifact.artifact_type,
                    artifact.updated_at.isoformat(),
                ]
            )
        )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _build_coverage(
    sources: list[SourceData],
    period_label: str | None,
    categories: dict[int, list[str]],
) -> dict:
    teams = sorted({_plain_value(source.team_label) for source in sources})
    labels = sorted({label for source_labels in categories.values() for label in source_labels})
    summary = (
        f"{len(sources)} ready sources across {len(teams)} teams and {len(labels)} labels."
        if sources
        else "No ready sources overlap the requested period."
    )
    return {
        "total_sources": len(sources),
        "totalSources": len(sources),
        "ready_sources": len(sources),
        "readySources": len(sources),
        "excluded_sources": 0,
        "excludedSources": 0,
        "period_label": period_label,
        "periodLabel": period_label,
        "teams": teams,
        "labels": labels,
        "summary": summary,
        "notes": ["LLM synthesis is grounded in ready Source Artifacts for this period."],
    }


def _build_source_cards(
    sources: list[SourceData],
    artifacts: list[SourceArtifact],
    categories: dict[int, list[str]],
) -> list[dict]:
    grouped = _group_artifacts(artifacts)
    cards: list[dict] = []
    for source in sources:
        source_id = source.id or 0
        by_type = grouped.get(source_id, {})
        summary_art = _latest_artifact(by_type.get("source_summary", []))
        content_art = _latest_artifact(by_type.get("source_content", []))
        insight_art = _latest_artifact(by_type.get("source_insight", []))
        summary_data = _artifact_data(summary_art)
        content_data = _artifact_data(content_art)
        chunk_count = len(content_data.get("chunks", [])) if isinstance(content_data.get("chunks"), list) else 0
        stats = dict(summary_data.get("statistics", {})) if isinstance(summary_data.get("statistics"), dict) else {}
        if "page_count" in summary_data:
            stats.setdefault("page_count", summary_data.get("page_count"))
        if chunk_count:
            stats.setdefault("chunk_count", chunk_count)

        evidence_refs = []
        for artifact in (summary_art, insight_art, content_art):
            if artifact is not None:
                evidence_refs.append({
                    "sourceId": source_id,
                    "sourceTitle": source.title,
                    "artifactId": artifact.id,
                })

        card = {
            "sourceId": source_id,
            "source_id": source_id,
            "title": source.title,
            "summary": summary_data.get("summary", ""),
            "sourceFileType": _plain_value(source.file_type),
            "file_type": _plain_value(source.file_type),
            "teamLabel": _plain_value(source.team_label),
            "team_label": _plain_value(source.team_label),
            "categoryLabels": categories.get(source_id, []),
            "category_labels": categories.get(source_id, []),
            "periodLabel": derive_period_label(source.period_start_month, source.period_end_month),
            "period_start_month": source.period_start_month,
            "period_end_month": source.period_end_month,
            "statistics": stats,
            "warnings": summary_data.get("warnings", []),
            "evidenceRefs": evidence_refs,
            "evidence_refs": evidence_refs,
        }
        cards.append(card)
    return cards


def _build_artifact_payload(
    sources: list[SourceData],
    artifacts: list[SourceArtifact],
    period_start_month: str,
    period_end_month: str,
    period_label: str | None,
    categories: dict[int, list[str]],
) -> dict:
    grouped = _group_artifacts(artifacts)
    payload_sources: list[dict] = []
    for source in sources:
        source_id = source.id or 0
        by_type = grouped.get(source_id, {})
        summary_art = _latest_artifact(by_type.get("source_summary", []))
        content_art = _latest_artifact(by_type.get("source_content", []))
        insight_art = _latest_artifact(by_type.get("source_insight", []))

        summary_data = _artifact_data(summary_art)
        content_data = _artifact_data(content_art)
        insight_data = _artifact_data(insight_art)
        chunks = content_data.get("chunks", []) if isinstance(content_data.get("chunks"), list) else []
        sample_refs = [
            {
                "chunk_id": chunk.get("chunk_id"),
                "summary": chunk.get("summary") or chunk.get("text", "")[:240],
                "page_number": chunk.get("page_number"),
            }
            for chunk in chunks[:5]
            if isinstance(chunk, dict)
        ]

        payload_sources.append({
            "source_id": source_id,
            "title": source.title,
            "file_type": _plain_value(source.file_type),
            "team_label": _plain_value(source.team_label),
            "category_labels": categories.get(source_id, []),
            "period_start_month": source.period_start_month,
            "period_end_month": source.period_end_month,
            "artifacts": {
                "source_summary": {
                    "artifact_id": summary_art.id if summary_art else None,
                    "summary": summary_data.get("summary", ""),
                    "statistics": summary_data.get("statistics", {}),
                    "page_count": summary_data.get("page_count"),
                    "warnings": summary_data.get("warnings", []),
                },
                "source_insight": {
                    "artifact_id": insight_art.id if insight_art else None,
                    "findings": insight_data.get("findings", insight_data.get("key_findings", [])),
                    "risks": insight_data.get("risks", []),
                    "opportunities": insight_data.get("opportunities", []),
                    "assumptions": insight_data.get("assumptions", []),
                    "quotes": insight_data.get("quotes", insight_data.get("source_quotes", [])),
                    "warnings": insight_data.get("warnings", []),
                },
                "source_content": {
                    "artifact_id": content_art.id if content_art else None,
                    "chunk_count": len(chunks),
                    "sample_refs": sample_refs,
                },
            },
        })

    return {
        "period": {
            "start": period_start_month,
            "end": period_end_month,
            "label": period_label,
        },
        "coverage": _build_coverage(sources, period_label, categories),
        "sources": payload_sources,
    }


def _normalize_llm_items(items: list[Any], kind: str) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        evidence_refs = [
            {
                "sourceId": ref.get("source_id"),
                "sourceTitle": ref.get("source_title"),
                "artifactId": ref.get("artifact_id"),
            }
            for ref in data.pop("evidence", [])
            if isinstance(ref, dict)
        ]
        normalized.append({
            "kind": data.get("kind") or kind,
            "text": data.get("text", ""),
            "confidence": data.get("confidence", "medium"),
            "theme": data.get("theme"),
            "evidenceRefs": evidence_refs,
            "evidence_refs": evidence_refs,
        })
    return normalized


def _compose_content(
    sources: list[SourceData],
    artifacts: list[SourceArtifact],
    period_label: str | None,
    categories: dict[int, list[str]] | None = None,
    fingerprint: str | None = None,
) -> dict:
    """Deterministic fallback content_json from sources and artifacts."""
    categories = categories or {source.id or 0: [] for source in sources}
    summaries: list[dict] = []
    insights: list[dict] = []

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

    source_cards = _build_source_cards(sources, artifacts, categories)

    # Extract findings from insights
    key_findings: list[dict] = []
    for ins in insights:
        data = ins.get("data", {})
        findings = data.get("findings", data.get("key_findings", []))
        for finding in findings:
            key_findings.append({
                "kind": "finding",
                "text": finding.get("text", ""),
                "confidence": finding.get("confidence", "medium"),
                "evidenceRefs": [{
                    "sourceId": ins["source_id"],
                    "artifactId": ins["artifact_id"],
                }],
            })

    coverage = _build_coverage(sources, period_label, categories)
    coverage["sources"] = source_cards

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
        "executive_summary": coverage["summary"],
        "cross_source_patterns": [],
        "source_cards": source_cards,
        "key_findings": key_findings,
        "risks_assumptions": [],
        "opportunities": [],
        "gaps": [{"kind": "gap", "text": gap} for gap in gaps],
        "confidence_assessment": "low" if gaps else "medium",
        "_fingerprint": fingerprint,
        "_composition_mode": "deterministic_fallback",
    }


def _compose_content_with_llm(
    sources: list[SourceData],
    artifacts: list[SourceArtifact],
    period_start_month: str,
    period_end_month: str,
    period_label: str | None,
    categories: dict[int, list[str]],
    fingerprint: str,
) -> dict:
    settings = get_settings()
    if not settings.rag_openai_api_key:
        raise RuntimeError("RAG_OPENAI_API_KEY is not configured")

    payload = _build_artifact_payload(
        sources=sources,
        artifacts=artifacts,
        period_start_month=period_start_month,
        period_end_month=period_end_month,
        period_label=period_label,
        categories=categories,
    )
    client = create_openai_client(
        base_url=settings.rag_openai_api_base_url,
        api_key=settings.rag_openai_api_key,
    )
    result = extract_visualization_snapshot(
        client=client,
        model=settings.rag_generation_model,
        artifact_payload=payload,
    )

    source_cards = _build_source_cards(sources, artifacts, categories)
    coverage = _build_coverage(sources, period_label, categories)
    coverage["sources"] = source_cards
    gaps = [{"kind": "gap", "text": gap} for gap in result.gaps]
    return {
        "coverage": coverage,
        "executive_summary": result.executive_summary,
        "cross_source_patterns": _normalize_llm_items(result.cross_source_patterns, "pattern"),
        "source_cards": source_cards,
        "key_findings": _normalize_llm_items(result.key_findings, "finding"),
        "risks_assumptions": _normalize_llm_items(result.risks_assumptions, "risk"),
        "opportunities": _normalize_llm_items(result.opportunities, "opportunity"),
        "gaps": gaps,
        "confidence_assessment": result.confidence_assessment,
        "_fingerprint": fingerprint,
        "_composition_mode": "llm",
    }


def _snapshot_to_read(snapshot: VisualizationSnapshot) -> VisualizationSnapshotRead:
    return VisualizationSnapshotRead(
        id=snapshot.id or 0,
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


def _load_scope_data(
    session: Session,
    workspace_id: int,
    period_start_month: str,
    period_end_month: str,
) -> tuple[list[SourceData], list[int], list[SourceArtifact], list[int], dict[int, list[str]], str]:
    sources = _query_overlapping_sources(session, workspace_id, period_start_month, period_end_month)
    source_ids = [source.id for source in sources if source.id is not None]
    artifacts = _collect_artifacts(session, source_ids)
    artifact_ids = [artifact.id for artifact in artifacts if artifact.id is not None]
    categories = _category_labels_by_source(session, source_ids)
    fingerprint = _compute_fingerprint(sources, artifacts, categories)
    return sources, source_ids, artifacts, artifact_ids, categories, fingerprint


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

    sources, source_ids, artifacts, artifact_ids, categories, fingerprint = _load_scope_data(
        session, workspace_id, period_start_month, period_end_month
    )

    cached = _find_cached(session, workspace_id, period_start_month, period_end_month)
    if cached is not None:
        cached_fingerprint = (cached.content_json or {}).get("_fingerprint")
        if cached_fingerprint != fingerprint:
            session.delete(cached)
            session.flush()
        else:
            return _snapshot_to_read(cached)

    return _compose_and_save(
        session,
        workspace_id,
        period_start_month,
        period_end_month,
        sources=sources,
        source_ids=source_ids,
        artifacts=artifacts,
        artifact_ids=artifact_ids,
        categories=categories,
        fingerprint=fingerprint,
    )


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
    sources: list[SourceData] | None = None,
    source_ids: list[int] | None = None,
    artifacts: list[SourceArtifact] | None = None,
    artifact_ids: list[int] | None = None,
    categories: dict[int, list[str]] | None = None,
    fingerprint: str | None = None,
) -> VisualizationSnapshotRead:
    """Compose snapshot content, persist it, and return the read schema."""
    if sources is None or source_ids is None or artifacts is None or artifact_ids is None or categories is None or fingerprint is None:
        sources, source_ids, artifacts, artifact_ids, categories, fingerprint = _load_scope_data(
            session, workspace_id, period_start_month, period_end_month
        )

    period_label = derive_period_label(period_start_month, period_end_month)
    title = f"Visualization: {period_label or f'{period_start_month} – {period_end_month}'}"
    generation_error: str | None = None
    try:
        if sources and artifacts:
            content = _compose_content_with_llm(
                sources=sources,
                artifacts=artifacts,
                period_start_month=period_start_month,
                period_end_month=period_end_month,
                period_label=period_label,
                categories=categories,
                fingerprint=fingerprint,
            )
        else:
            content = _compose_content(sources, artifacts, period_label, categories, fingerprint)
    except Exception as exc:  # noqa: BLE001 - fallback keeps Visualization page available.
        logger.warning("LLM visualization composition failed; using deterministic fallback: %s", exc)
        generation_error = f"LLM visualization failed; using deterministic fallback: {exc}"
        content = _compose_content(sources, artifacts, period_label, categories, fingerprint)

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
        generation_error=generation_error,
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
