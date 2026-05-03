from pydantic import BaseModel

from app.models.enums import ChatMessageRole, ChatMessageType


class ChatMessageRead(BaseModel):
    id: int
    session_id: int
    role: ChatMessageRole
    content: str
    message_type: ChatMessageType
