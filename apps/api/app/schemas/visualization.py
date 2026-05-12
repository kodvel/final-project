"""Visualization schemas — snapshot-based responses."""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ArtifactType, CategoryLabel, TeamLabel


# Legacy kept for backward compat with artifact-level tests
class VisualizationArtifactRead(BaseModel):
    id: int
    source_id: int
    artifact_type: ArtifactType
    title: str
    content_json: dict
    source_title: str | None = None
    source_file_type: str | None = None
    team_label: TeamLabel | None = None
    category_labels: list[CategoryLabel] | None = None


class VisualizationSnapshotRead(BaseModel):
    id: int
    workspace_id: int
    period_start_month: str
    period_end_month: str
    title: str
    content_json: dict
    source_ids_json: list[int]
    artifact_ids_json: list[int]
    status: str
    generation_error: str | None = None
    generated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
