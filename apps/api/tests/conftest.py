"""Test fixtures for isolated API tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from app.db import base  # noqa: F401
from app.db.session import get_session


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db_url = f"sqlite:///{tmp_path / 'test.db'}"

    # Create test engine first
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    # Patch storage path
    monkeypatch.setattr("app.storage.local.UPLOADS_ROOT", tmp_path / "uploads")
    (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)

    # Patch get_settings to return test db URL
    from app.core import config
    # Clear cache before patching so we get a fresh settings object
    config.get_settings.cache_clear()
    original_get_settings = config.get_settings

    test_settings = original_get_settings()
    test_settings.database_url = test_db_url

    def override_get_settings():
        return test_settings

    # Replace get_settings with our override
    monkeypatch.setattr("app.core.config.get_settings", override_get_settings)

    # Patch module-level engine in session module so lifespan uses test engine
    from app.db import session as db_session_module
    monkeypatch.setattr(db_session_module, "engine", test_engine)
    monkeypatch.setattr(db_session_module, "init_db", lambda: None)
    # Patch seed_default_workspaces so lifespan doesn't try to access real db
    monkeypatch.setattr("app.services.workspaces.seed_default_workspaces", lambda session: None)

    # Override get_session dependency
    def override_get_session():
        with Session(test_engine) as session:
            yield session

    from app.main import app
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    test_engine.dispose()
