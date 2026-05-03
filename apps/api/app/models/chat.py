from datetime import datetime
from typing import ClassVar

from sqlmodel import Field, SQLModel

from app.models.enums import ChatMessageRole, ChatMessageType


class ChatSession(SQLModel, table=True):
    __tablename__: ClassVar[str] = "chat_session"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(index=True, foreign_key="workspace.id")
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(SQLModel, table=True):
    __tablename__: ClassVar[str] = "chat_message"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="chat_session.id")
    role: ChatMessageRole
    content: str
    message_type: ChatMessageType = ChatMessageType.NORMAL
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentToolCall(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_tool_call"

    id: int | None = Field(default=None, primary_key=True)
    message_id: int = Field(index=True, foreign_key="chat_message.id")
    tool_name: str
    status: str
    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageSourceCitation(SQLModel, table=True):
    __tablename__: ClassVar[str] = "message_source_citation"

    id: int | None = Field(default=None, primary_key=True)
    message_id: int = Field(index=True, foreign_key="chat_message.id")
    source_id: int = Field(index=True, foreign_key="source_data.id")
    artifact_id: int | None = Field(default=None, foreign_key="source_artifact.id")
    quote: str | None = None
    page_number: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
