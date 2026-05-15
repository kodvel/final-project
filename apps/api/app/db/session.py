from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from app.core.config import get_settings


def create_db_engine() -> Engine:
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = create_db_engine()


def get_session() -> Session:
    with Session(engine) as session:
        yield session
