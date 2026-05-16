from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.services import workspaces as workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    data: WorkspaceCreate,
    session: Session = Depends(get_session),
) -> WorkspaceRead:
    workspace = workspace_service.create_workspace(session, data)
    return WorkspaceRead.model_validate(workspace)


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(
    session: Session = Depends(get_session),
) -> list[WorkspaceRead]:
    results = workspace_service.list_workspaces(session)
    return [WorkspaceRead.model_validate(w) for w in results]


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(
    workspace_id: int,
    session: Session = Depends(get_session),
) -> WorkspaceRead:
    workspace = workspace_service.get_workspace(session, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceRead.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    workspace_id: int,
    data: WorkspaceUpdate,
    session: Session = Depends(get_session),
) -> WorkspaceRead:
    try:
        workspace = workspace_service.update_workspace(session, workspace_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceRead.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    session: Session = Depends(get_session),
) -> Response:
    if not workspace_service.delete_workspace(session, workspace_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
