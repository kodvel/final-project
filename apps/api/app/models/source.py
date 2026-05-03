from datetime import datetime
from typing import ClassVar

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import CategoryLabel, ProcessingStatus, SourceFileType, TeamLabel


class SourceData(SQLModel, table=True):
    __tablename__: ClassVar[str] = "source_data"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(index=True, foreign_key="workspace.id")
    title: str
    team_label: TeamLabel
    file_type: SourceFileType
    original_filename: str
    storage_path: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    period_label: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.UPLOADED
    processing_error: str | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SourceCategory(SQLModel, table=True):
    __tablename__: ClassVar[str] = "source_category"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(index=True, foreign_key="source_data.id")
    category: CategoryLabel
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SourceArtifact(SQLModel, table=True):
    __tablename__: ClassVar[str] = "source_artifact"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(index=True, foreign_key="source_data.id")
    artifact_type: str
    title: str
    content_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
