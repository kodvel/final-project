"""Visualization Snapshot model — cached period-based intelligence view."""

from datetime import datetime
from typing import ClassVar

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class VisualizationSnapshot(SQLModel, table=True):
    __tablename__: ClassVar[str] = "visualization_snapshot"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(index=True, foreign_key="workspace.id")
    period_start_month: str
    period_end_month: str
    scope_hash: str = Field(default="", index=True)
    title: str = ""
    content_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source_ids_json: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    artifact_ids_json: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    status: str = "ready"
    generation_error: str | None = None
    generated_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
