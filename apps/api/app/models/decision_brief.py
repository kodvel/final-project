from datetime import datetime
from typing import ClassVar

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import DecisionApprovalStatus, DecisionRecommendationStatus


class DecisionBrief(SQLModel, table=True):
    __tablename__: ClassVar[str] = "decision_brief"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(index=True, foreign_key="workspace.id")
    chat_session_id: int = Field(index=True, foreign_key="chat_session.id")
    chat_message_id: int = Field(index=True, foreign_key="chat_message.id")
    sequence_number: int = Field(default=1)
    title: str
    objective: str | None = Field(default=None)
    recommendation_status: DecisionRecommendationStatus
    approval_status: DecisionApprovalStatus = DecisionApprovalStatus.DRAFT
    content_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    context_cutoff_message_id: int | None = Field(default=None)
    status_updated_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
