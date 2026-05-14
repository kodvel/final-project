from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DecisionApprovalStatus, DecisionRecommendationStatus


# ---------------------------------------------------------------------------
# LLM structured-output schema
# ---------------------------------------------------------------------------


class DecisionBriefEvidenceRef(BaseModel):
    """A reference to a citation already present in the chat session."""

    ordinal: int = Field(description="The citation ordinal in the chat session (1-indexed).")
    note: str | None = Field(
        default=None,
        description="One-line note explaining how this evidence supports the brief section.",
    )


class DecisionBriefContent(BaseModel):
    """Structured Decision Brief content produced by the LLM."""

    title: str = Field(description="Short title summarising the decision being framed.")
    objective: str = Field(description="One-paragraph statement of the decision under consideration.")
    context_problem: str = Field(description="Problem framing and background.")
    source_evidence: list[DecisionBriefEvidenceRef] = Field(
        default_factory=list,
        description="References to session citations that ground the brief.",
    )
    strategic_interpretation: str = Field(description="How the evidence shapes strategic options.")
    recommendation: str = Field(description="The recommended action.")
    alternatives_considered: list[str] = Field(default_factory=list)
    risks_assumptions: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    recommendation_status: DecisionRecommendationStatus = Field(
        description="Overall recommendation: go, no_go, or validate_first.",
    )


# ---------------------------------------------------------------------------
# API request / response schemas
# ---------------------------------------------------------------------------


class DecisionBriefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    chat_session_id: int
    chat_message_id: int
    sequence_number: int
    context_cutoff_message_id: int | None = None
    title: str
    objective: str | None = None
    recommendation_status: DecisionRecommendationStatus
    approval_status: DecisionApprovalStatus
    content_json: dict
    created_at: datetime
    updated_at: datetime
    status_updated_at: datetime


class DecisionBriefStatusUpdate(BaseModel):
    workspace_id: int
    approval_status: DecisionApprovalStatus
