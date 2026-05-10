from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DecisionApprovalStatus, DecisionRecommendationStatus


class DecisionBriefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    chat_session_id: int
    chat_message_id: int
    title: str
    recommendation_status: DecisionRecommendationStatus
    approval_status: DecisionApprovalStatus
    content_json: dict
    created_at: datetime
    updated_at: datetime
