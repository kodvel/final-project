from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import ChatMessageRole, ChatMessageType, CitationStatus, CitationType, MessageStatus


class ChatSession(SQLModel, table=True):
    __tablename__: ClassVar[str] = "chat_session"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(index=True, foreign_key="workspace.id")
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime | None = None
    conversation_summary: str | None = None
    summary_cutoff_message_id: int | None = None
    summary_updated_at: datetime | None = None


class ChatMessage(SQLModel, table=True):
    __tablename__: ClassVar[str] = "chat_message"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="chat_session.id")
    role: ChatMessageRole
    content: str
    message_type: ChatMessageType = ChatMessageType.NORMAL
    status: MessageStatus = MessageStatus.COMPLETED
    error_message: str | None = None
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class AgentToolCall(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_tool_call"

    id: int | None = Field(default=None, primary_key=True)
    message_id: int = Field(index=True, foreign_key="chat_message.id")
    call_id: str | None = Field(default=None, index=True)
    tool_name: str
    status: str
    summary: str
    input_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    output_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageSourceCitation(SQLModel, table=True):
    __tablename__: ClassVar[str] = "message_source_citation"

    id: int | None = Field(default=None, primary_key=True)
    message_id: int = Field(index=True, foreign_key="chat_message.id")
    source_id: int | None = Field(default=None, index=True, foreign_key="source_data.id", nullable=True)
    artifact_id: int | None = Field(default=None, foreign_key="source_artifact.id")
    chunk_id: str | None = None
    citation_type: CitationType = CitationType.UPLOADED_SOURCE
    ordinal: int | None = None
    quote: str | None = None
    page_number: int | None = None
    url: str | None = None
    title: str | None = None
    domain: str | None = None
    provider: str | None = None
    provider_request_id: str | None = None
    published_date: datetime | None = None
    favicon_url: str | None = None
    snippet: str | None = None
    row_refs_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    relevance_score: float | None = None
    citation_status: CitationStatus = CitationStatus.AVAILABLE
    retrieved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
