from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.decision_brief import DecisionBrief
from app.models.enums import DecisionApprovalStatus
from app.schemas.decision_brief import DecisionBriefRead

router = APIRouter(prefix="/decision-briefs", tags=["decision briefs"])

# Valid transitions: current_status -> set of allowed next statuses
_TRANSITIONS: dict[DecisionApprovalStatus, set[DecisionApprovalStatus]] = {
    DecisionApprovalStatus.DRAFT: {
        DecisionApprovalStatus.REVIEWED,
        DecisionApprovalStatus.APPROVED,
        DecisionApprovalStatus.REJECTED,
    },
    DecisionApprovalStatus.REVIEWED: {
        DecisionApprovalStatus.APPROVED,
        DecisionApprovalStatus.REJECTED,
    },
    DecisionApprovalStatus.APPROVED: set(),
    DecisionApprovalStatus.REJECTED: set(),
}


class StatusUpdatePayload(BaseModel):
    approval_status: DecisionApprovalStatus


@router.patch("/{brief_id}/status", response_model=DecisionBriefRead)
def update_brief_status(
    brief_id: int,
    payload: StatusUpdatePayload,
    workspace_id: int = Query(..., description="Workspace ID for scope validation"),
    session: Session = Depends(get_session),
) -> DecisionBriefRead:
    """Update the approval_status of a Decision Brief through valid transitions only."""
    brief = session.exec(
        select(DecisionBrief).where(
            DecisionBrief.id == brief_id,
            DecisionBrief.workspace_id == workspace_id,
        )
    ).first()

    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision Brief not found")

    current = DecisionApprovalStatus(brief.approval_status)
    allowed = _TRANSITIONS.get(current, set())

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Decision Brief is locked at status '{current.value}' and cannot be updated.",
        )

    if payload.approval_status not in allowed:
        allowed_labels = ", ".join(sorted(s.value for s in allowed))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot transition from '{current.value}' to '{payload.approval_status.value}'. Allowed: {allowed_labels}.",
        )

    brief.approval_status = payload.approval_status
    brief.status_updated_at = datetime.utcnow()
    brief.updated_at = datetime.utcnow()
    session.add(brief)
    session.commit()
    session.refresh(brief)
    return DecisionBriefRead.model_validate(brief)
