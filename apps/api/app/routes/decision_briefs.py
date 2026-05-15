from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.decision_brief import DecisionBrief
from app.models.enums import DecisionApprovalStatus
from app.schemas.decision_brief import DecisionBriefRead, DecisionBriefStatusUpdate
from app.services import decision_briefs as decision_brief_service

router = APIRouter(prefix="/decision-briefs", tags=["decision briefs"])


def _load_brief(session: Session, brief_id: int, workspace_id: int) -> DecisionBrief:
    brief = session.get(DecisionBrief, brief_id)
    if brief is None or brief.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision Brief not found")
    return brief


@router.get("", response_model=list[DecisionBriefRead])
def list_decision_briefs(
    workspace_id: int = Query(..., description="Workspace ID from client-selected active workspace"),
    approval_status: DecisionApprovalStatus | None = Query(
        None, description="Optional approval status filter"
    ),
    session: Session = Depends(get_session),
) -> list[DecisionBriefRead]:
    """List Decision Briefs scoped to the workspace, newest first."""
    statement = (
        select(DecisionBrief)
        .where(DecisionBrief.workspace_id == workspace_id)
        .order_by(desc(DecisionBrief.created_at), desc(DecisionBrief.sequence_number))
    )
    if approval_status is not None:
        statement = statement.where(DecisionBrief.approval_status == approval_status)
    rows = session.exec(statement).all()
    return [DecisionBriefRead.model_validate(row) for row in rows]


@router.get("/{brief_id}", response_model=DecisionBriefRead)
def get_decision_brief(
    brief_id: int,
    workspace_id: int = Query(..., description="Workspace ID from client-selected active workspace"),
    session: Session = Depends(get_session),
) -> DecisionBriefRead:
    """Get a single Decision Brief, workspace-scoped."""
    brief = _load_brief(session, brief_id, workspace_id)
    return DecisionBriefRead.model_validate(brief)


@router.patch("/{brief_id}/status", response_model=DecisionBriefRead)
def update_decision_brief_status(
    brief_id: int,
    payload: DecisionBriefStatusUpdate,
    session: Session = Depends(get_session),
) -> DecisionBriefRead:
    """Transition a Decision Brief through the approval state machine."""
    brief = _load_brief(session, brief_id, payload.workspace_id)
    try:
        updated = decision_brief_service.transition_status(session, brief, payload.approval_status)
    except decision_brief_service.InvalidStatusTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return DecisionBriefRead.model_validate(updated)
