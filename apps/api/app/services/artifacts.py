"""Centralized SourceArtifact CRUD helpers.

All artifact writes should go through this service so that upsert logic,
type validation, and future indexing hooks stay in one place.
"""

from datetime import datetime

from sqlmodel import Session, select

from app.models.enums import ArtifactType
from app.models.source import SourceArtifact


def upsert_source_artifact(
    session: Session,
    source_id: int,
    artifact_type: ArtifactType | str,
    title: str,
    content_json: dict,
) -> SourceArtifact:
    """Create or update a single artifact for a source (keyed by type).

    If an artifact of the same *artifact_type* already exists for the source,
    its title, content, and updated_at are replaced in-place.
    """
    existing = session.exec(
        select(SourceArtifact).where(
            SourceArtifact.source_id == source_id,
            SourceArtifact.artifact_type == str(artifact_type),
        )
    ).first()

    if existing:
        existing.title = title
        existing.content_json = content_json
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        return existing

    artifact = SourceArtifact(
        source_id=source_id,
        artifact_type=str(artifact_type),
        title=title,
        content_json=content_json,
    )
    session.add(artifact)
    return artifact


def get_source_artifact(
    session: Session,
    source_id: int,
    artifact_type: ArtifactType | str,
) -> SourceArtifact | None:
    """Return the single artifact matching *artifact_type* for a source, or None."""
    return session.exec(
        select(SourceArtifact).where(
            SourceArtifact.source_id == source_id,
            SourceArtifact.artifact_type == str(artifact_type),
        )
    ).first()


def list_source_artifacts(
    session: Session,
    source_id: int,
) -> list[SourceArtifact]:
    """Return all artifacts for a source."""
    return list(
        session.exec(
            select(SourceArtifact).where(SourceArtifact.source_id == source_id)
        ).all()
    )


def replace_source_artifacts(
    session: Session,
    source_id: int,
    artifacts: list[SourceArtifact],
) -> list[SourceArtifact]:
    """Delete all existing artifacts for a source and replace with *artifacts*.

    Useful for retry / reprocessing flows where the full artifact set is
    regenerated from scratch.
    """
    existing = list_source_artifacts(session, source_id)
    for art in existing:
        session.delete(art)
    session.flush()

    for art in artifacts:
        art.source_id = source_id
        session.add(art)
    session.flush()
    return artifacts
