"""Workspace domain orchestration."""

from sqlmodel import Session, select

from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate

SEED_WORKSPACES = (
    ("Developer 1", "Default workspace for Developer 1."),
    ("Developer 2", "Default workspace for Developer 2."),
    ("Developer 3", "Default workspace for Developer 3."),
    ("Demo", "Default workspace for final demo."),
)


def seed_default_workspaces(session: Session) -> None:
    existing_names = set(session.exec(select(Workspace.name)).all())
    for name, description in SEED_WORKSPACES:
        if name not in existing_names:
            session.add(Workspace(name=name, description=description))
    session.commit()


def create_workspace(session: Session, data: WorkspaceCreate) -> Workspace:
    workspace = Workspace(name=data.name, description=data.description)
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace


def list_workspaces(session: Session) -> list[Workspace]:
    return list(session.exec(select(Workspace)).all())


def get_workspace(session: Session, workspace_id: int) -> Workspace | None:
    return session.get(Workspace, workspace_id)
