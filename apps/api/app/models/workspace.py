from datetime import datetime
from typing import ClassVar

from sqlmodel import Field, SQLModel


class Workspace(SQLModel, table=True):
    __tablename__: ClassVar[str] = "workspace"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
