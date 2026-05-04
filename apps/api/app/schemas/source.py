from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CategoryLabel, ProcessingStatus, SourceFileType, TeamLabel


class SourceCreate(BaseModel):
    workspace_id: int
    title: str
    team_label: TeamLabel
    category_labels: list[CategoryLabel]
    file_type: SourceFileType
    original_filename: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    period_label: str | None = None


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    title: str
    team_label: TeamLabel
    category_labels: list[CategoryLabel]
    file_type: SourceFileType
    processing_status: ProcessingStatus
    processing_error: str | None = None
    original_filename: str
    storage_path: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    period_label: str | None = None
    uploaded_at: datetime
    processed_at: datetime | None = None
    deleted_at: datetime | None = None
