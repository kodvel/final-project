from collections.abc import Iterator

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def create_db_engine() -> Engine:
    connect_args = {"check_same_thread": False} if get_settings().database_url.startswith("sqlite") else {}
    return create_engine(get_settings().database_url, connect_args=connect_args)


engine = create_db_engine()


def init_db() -> None:
    from app.db import base  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
