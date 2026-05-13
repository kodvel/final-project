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

    # --- Mock CSV LLM extraction to avoid real API calls ---
    _install_csv_llm_mocks(monkeypatch)

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


def _install_csv_llm_mocks(monkeypatch):
    """Replace ``llm_extraction.extract_csv_*`` with deterministic fakes.

    The fakes inspect the compact profile data and produce artefacts that
    satisfy existing Task 2 / Task 1 test assertions (column references,
    finding texts, stable chunk IDs, etc.).
    """
    from app.services import llm_extraction

    def _fake_csv_content(client, model, profile_data):
        columns = profile_data.get("columns", [])
        chunks: list[llm_extraction.CSVContentChunk] = []
        for i, col in enumerate(columns):
            name = col.get("name", f"col_{i}")
            inferred = col.get("inferred_type", "text")
            parts: list[str] = [f"Column '{name}' ({inferred}): "]
            stats = col.get("numeric_stats")
            if stats:
                parts.append(
                    f"ranges {stats['min']:.2f}–{stats['max']:.2f}, "
                    f"avg {stats['avg']:.2f} ({stats.get('count', 0)} values, "
                    f"{col.get('null_count', 0)} nulls, {col.get('unique_count', 0)} unique)"
                )
            else:
                parts.append(f"{col.get('unique_count', 0)} unique, {col.get('null_count', 0)} nulls")
                samples = col.get("sample_values", [])
                if samples:
                    parts.append(f", samples: [{', '.join(str(v) for v in samples[:3])}]")
            chunks.append(
                llm_extraction.CSVContentChunk(
                    chunk_id=f"csv-profile-{i}",
                    text="".join(parts),
                    content_type="metric" if inferred == "numeric" else "metadata",
                    document_section="data_profile",
                    chunk_index=i,
                    columns=[name],
                )
            )
        # Summary chunk referencing all numeric columns
        numeric_cols = [c for c in columns if c.get("numeric_stats")]
        if numeric_cols:
            lines = [f"Dataset: {profile_data.get('row_count', 0)} rows × {profile_data.get('column_count', 0)} columns."]
            for c in numeric_cols:
                s = c.get("numeric_stats", {})
                lines.append(f"{c['name']}: min={s['min']:.2f}, max={s['max']:.2f}, avg={s['avg']:.2f}")
            chunks.append(
                llm_extraction.CSVContentChunk(
                    chunk_id=f"csv-profile-{len(columns)}",
                    text=" ".join(lines),
                    content_type="metric",
                    document_section="data_summary",
                    chunk_index=len(columns),
                    columns=[c["name"] for c in numeric_cols],
                )
            )
        return llm_extraction.CSVContentResponse(
            summary=f"Column-level profiling for {profile_data.get('row_count', 0)} rows, "
            f"{profile_data.get('column_count', 0)} columns.",
            statistics={
                "row_count": profile_data.get("row_count"),
                "column_count": profile_data.get("column_count"),
                "chunk_count": len(chunks),
            },
            chunks=chunks,
            metadata={"delimiter": profile_data.get("delimiter", ","), "has_header": profile_data.get("has_header", True)},
        )

    def _fake_csv_insight(client, model, profile_data):
        findings: list[llm_extraction.FindingItem] = []
        risks: list[llm_extraction.FindingItem] = []
        warnings: list[str] = []
        for col in profile_data.get("columns", []):
            name = col.get("name", "")
            inferred = col.get("inferred_type", "text")
            if inferred == "numeric" and col.get("numeric_stats"):
                s = col["numeric_stats"]
                findings.append(
                    llm_extraction.FindingItem(
                        text=(
                            f"{name} ranges from {s['min']:.2f} to {s['max']:.2f}, "
                            f"with an average of {s['avg']:.2f} across {s['count']} records."
                        ),
                        confidence="high",
                    )
                )
            if inferred == "date" and col.get("date_stats"):
                ds = col["date_stats"]
                findings.append(
                    llm_extraction.FindingItem(
                        text=f"Data spans from {ds['min']} to {ds['max']}.",
                        confidence="high",
                    )
                )
            row_count = profile_data.get("row_count", 0)
            null_count = col.get("null_count", 0)
            if row_count > 0 and null_count / row_count > 0.3:
                warnings.append(f"Column '{name}' has {null_count} null values ({null_count / row_count * 100:.0f}%).")
        # Ensure at least a basic overview finding
        if not findings:
            findings.append(
                llm_extraction.FindingItem(
                    text=f"Dataset contains {profile_data.get('row_count', 0)} rows and {profile_data.get('column_count', 0)} columns.",
                    confidence="high",
                )
            )
        return llm_extraction.CSVInsightResponse(
            findings=findings,
            risks=risks,
            opportunities=[],
            assumptions=[],
            warnings=warnings,
        )

    monkeypatch.setattr(llm_extraction, "extract_csv_content", _fake_csv_content)
    monkeypatch.setattr(llm_extraction, "extract_csv_insight", _fake_csv_insight)
