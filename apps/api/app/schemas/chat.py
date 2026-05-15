from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

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
    trace_url: str | None = None
    decision_brief_id: int | None = None
    decision_brief_title: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _compute_trace_url(self) -> "ChatMessageRead":
        if self.trace_id and not self.trace_url:
            from app.core.config import get_settings
            host = get_settings().langfuse_host.rstrip("/")
            self.trace_url = f"{host}/trace/{self.trace_id}"
        return self
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


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    source_id: int | None = None
    artifact_id: int | None = None
    chunk_id: str | None = None
    citation_type: CitationType = CitationType.UPLOADED_SOURCE
    ordinal: int | None = None
    quote: str | None = None
    snippet: str | None = None
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
    call_id: str | None = None
    tool_name: str
    status: str
    summary: str


class ChatSessionDetail(ChatSessionRead):
    messages: list[ChatMessageRead]
    citations: list[CitationRead] = []
    tool_calls: list[ToolCallRead] = []


# ---------------------------------------------------------------------------
# Streaming / SSE schemas
# ---------------------------------------------------------------------------

class ChatStreamRequest(BaseModel):
    workspace_id: int
    session_id: int | None = None
    message: str
