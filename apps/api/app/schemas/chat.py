from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ChatMessageRole, ChatMessageType


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
    trace_id: str | None = None
    created_at: datetime


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionRead):
    messages: list[ChatMessageRead]


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessagePairRead(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
