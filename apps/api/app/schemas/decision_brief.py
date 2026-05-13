from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DecisionApprovalStatus, DecisionRecommendationStatus


class DecisionBriefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    chat_session_id: int
    chat_message_id: int
    sequence_number: int
    title: str
    objective: str | None
    recommendation_status: DecisionRecommendationStatus
    approval_status: DecisionApprovalStatus
    content_json: dict
    context_cutoff_message_id: int | None
    status_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
