from pydantic import BaseModel


class VisualizationArtifactRead(BaseModel):
    id: int
    source_id: int
    artifact_type: str
    title: str
    content_json: dict
