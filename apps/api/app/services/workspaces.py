"""Workspace domain orchestration."""

import datetime
import logging
import shutil
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

from app.helpers import storage as storage_helpers
from app.models.chat import AgentToolCall, ChatMessage, ChatSession, MessageSourceCitation
from app.models.decision_brief import DecisionBrief
from app.models.source import SourceArtifact, SourceCategory, SourceData
from app.models.visualization_snapshot import VisualizationSnapshot
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate

logger = logging.getLogger(__name__)

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


def update_workspace(session: Session, workspace_id: int, data: WorkspaceUpdate) -> Workspace | None:
    workspace = session.get(Workspace, workspace_id)
    if not workspace:
        return None
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise ValueError("name must not be empty")
        workspace.name = name
    if data.description is not None:
        workspace.description = data.description
    workspace.updated_at = datetime.datetime.utcnow()
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace


def delete_workspace(session: Session, workspace_id: int) -> bool:
    """Hard-delete a workspace and all dependent rows, files, and vectors.

    Returns False if the workspace does not exist.
    """
    workspace = session.get(Workspace, workspace_id)
    if not workspace:
        return False

    source_ids = list(
        session.exec(select(SourceData.id).where(SourceData.workspace_id == workspace_id)).all()
    )
    session_ids = list(
        session.exec(select(ChatSession.id).where(ChatSession.workspace_id == workspace_id)).all()
    )
    message_ids: list[int] = []
    if session_ids:
        message_ids = list(
            session.exec(select(ChatMessage.id).where(ChatMessage.session_id.in_(session_ids))).all()
        )
    brief_ids = list(
        session.exec(select(DecisionBrief.id).where(DecisionBrief.workspace_id == workspace_id)).all()
    )

    if message_ids:
        session.exec(delete(AgentToolCall).where(AgentToolCall.message_id.in_(message_ids)))
        session.exec(delete(MessageSourceCitation).where(MessageSourceCitation.message_id.in_(message_ids)))

    # DecisionBrief has FKs to both chat_message and chat_session, so delete it
    # before either of those tables.
    session.exec(delete(DecisionBrief).where(DecisionBrief.workspace_id == workspace_id))

    if message_ids:
        session.exec(delete(ChatMessage).where(ChatMessage.id.in_(message_ids)))
    session.exec(delete(ChatSession).where(ChatSession.workspace_id == workspace_id))

    if source_ids:
        session.exec(delete(SourceCategory).where(SourceCategory.source_id.in_(source_ids)))
        session.exec(delete(SourceArtifact).where(SourceArtifact.source_id.in_(source_ids)))
    session.exec(delete(SourceData).where(SourceData.workspace_id == workspace_id))

    session.exec(delete(VisualizationSnapshot).where(VisualizationSnapshot.workspace_id == workspace_id))
    session.delete(workspace)
    session.commit()

    try:
        from app.knowledge.indexing import delete_decision_brief_vectors, delete_source_vectors

        for sid in source_ids:
            try:
                delete_source_vectors(sid)
            except Exception:
                logger.warning("Failed to delete vectors for source %s", sid, exc_info=True)
        for bid in brief_ids:
            try:
                delete_decision_brief_vectors(bid)
            except Exception:
                logger.warning("Failed to delete vectors for brief %s", bid, exc_info=True)
    except Exception:
        logger.warning("Vector cleanup skipped for workspace %s", workspace_id, exc_info=True)

    upload_dir = Path(storage_helpers.UPLOADS_ROOT) / str(workspace_id)
    shutil.rmtree(upload_dir, ignore_errors=True)

    extracted_dir = Path("storage/extracted") / str(workspace_id)
    shutil.rmtree(extracted_dir, ignore_errors=True)

    return True
