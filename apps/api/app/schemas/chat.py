from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    ChatMessageRole,
    ChatMessageType,
    CitationStatus,
    CitationType,
    MessageStatus,
)


class ChatSessionCreate(BaseModel):
    workspace_id: int
    title: str | None = None


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: ChatMessageRole
    content: str
    message_type: ChatMessageType
    status: MessageStatus = MessageStatus.COMPLETED
    error_message: str | None = None
    metadata_json: dict[str, Any] | None = None
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None
    conversation_summary: str | None = None
    summary_cutoff_message_id: int | None = None
    summary_updated_at: datetime | None = None


class ChatSessionDetail(ChatSessionRead):
    messages: list[ChatMessageRead]


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessagePairRead(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead


# ---------------------------------------------------------------------------
# Streaming / SSE schemas
# ---------------------------------------------------------------------------

class ChatStreamRequest(BaseModel):
    workspace_id: int
    session_id: int | None = None
    message: str


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    source_id: int | None = None
    citation_type: CitationType = CitationType.UPLOADED_SOURCE
    ordinal: int | None = None
    quote: str | None = None
    page_number: int | None = None
    url: str | None = None
    title: str | None = None
    domain: str | None = None
    citation_status: CitationStatus = CitationStatus.AVAILABLE
    relevance_score: float | None = None


class ToolCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    tool_name: str
    status: str
    summary: str
