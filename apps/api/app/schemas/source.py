from pydantic import BaseModel

from app.models.enums import CategoryLabel, ProcessingStatus, SourceFileType, TeamLabel


class SourceRead(BaseModel):
    id: int
    workspace_id: int
    title: str
    team_label: TeamLabel
    category_labels: list[CategoryLabel]
    file_type: SourceFileType
    processing_status: ProcessingStatus
