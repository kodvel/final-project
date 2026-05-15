from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.decision_brief import DecisionBrief
from app.schemas.chat import (
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
    ChatStreamRequest,
    CitationRead,
    ToolCallRead,
)
from app.services import chat as chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    payload: ChatSessionCreate,
    session: Session = Depends(get_session),
) -> ChatSessionRead:
    """Create a Workspace-scoped Chat Session."""
    try:
        return chat_service.create_session(session, payload.workspace_id, payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_chat_sessions(
    workspace_id: int = Query(..., description="Workspace ID from client-selected active workspace"),
    limit: int = Query(5, ge=1, le=100, description="Max sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    session: Session = Depends(get_session),
) -> list[ChatSessionRead]:
    """List Chat Sessions for one Workspace, newest first, with pagination."""
    return [
        ChatSessionRead.model_validate(chat_session)
        for chat_session in chat_service.list_sessions(session, workspace_id, limit=limit, offset=offset)
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(
    session_id: int,
    workspace_id: int = Query(..., description="Workspace ID from client-selected active workspace"),
    session: Session = Depends(get_session),
) -> ChatSessionDetail:
    """Get one Chat Session with persisted messages, citations, and tool calls."""
    chat_session = chat_service.get_session_for_workspace(session, session_id, workspace_id)
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat Session not found")

    # Load citations and tool calls for all messages in the session
    citations = chat_service.list_citations_for_session(session, session_id)
    tool_calls = chat_service.list_tool_calls_for_session(session, session_id)

    # Map chat_message_id -> (decision_brief_id, title) so the frontend can render brief cards.
    briefs = session.exec(
        select(DecisionBrief).where(DecisionBrief.chat_session_id == session_id)
    ).all()
    brief_info_by_message: dict[int, tuple[int, str]] = {}
    for b in briefs:
        if b.id is not None:
            brief_info_by_message[b.chat_message_id] = (b.id, b.title)

    message_reads: list[ChatMessageRead] = []
    for message in chat_service.list_messages(session, session_id):
        read = ChatMessageRead.model_validate(message)
        if message.id in brief_info_by_message:
            brief_id, brief_title = brief_info_by_message[message.id]
            read.decision_brief_id = brief_id
            read.decision_brief_title = brief_title
        message_reads.append(read)

    return ChatSessionDetail(
        id=chat_session.id,
        workspace_id=chat_session.workspace_id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        last_message_at=chat_session.last_message_at,
        conversation_summary=chat_session.conversation_summary,
        summary_cutoff_message_id=chat_session.summary_cutoff_message_id,
        summary_updated_at=chat_session.summary_updated_at,
        messages=message_reads,
        citations=[CitationRead.model_validate(c) for c in citations],
        tool_calls=[ToolCallRead.model_validate(tc) for tc in tool_calls],
    )


@router.post("/messages/stream")
async def stream_chat_message(
    request: Request,
    payload: ChatStreamRequest,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Stream a chat interaction via SSE.

    Supports lazy session creation (no session_id → new session).
    Returns ``text/event-stream`` with DeltaKit-compatible SSE events.
    """
    return StreamingResponse(
        chat_service.stream_chat(session, payload.workspace_id, payload.session_id, payload.message, request.is_disconnected),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
