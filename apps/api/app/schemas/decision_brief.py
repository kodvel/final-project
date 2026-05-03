from pydantic import BaseModel

from app.models.enums import DecisionApprovalStatus, DecisionRecommendationStatus


class DecisionBriefRead(BaseModel):
    id: int
    title: str
    recommendation_status: DecisionRecommendationStatus
    approval_status: DecisionApprovalStatus
    content_json: dict
