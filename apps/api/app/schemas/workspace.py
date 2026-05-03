from pydantic import BaseModel


class WorkspaceRead(BaseModel):
    id: int
    name: str
    description: str | None = None
