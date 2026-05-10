from pydantic import BaseModel

from app.models.enums import ArtifactType, CategoryLabel, TeamLabel


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
