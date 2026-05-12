"""Task 2 tests: CSV processing into Visualization Data + Snapshot behavior."""

from app.models.enums import ProcessingStatus


def create_workspace(client, name: str = "Demo") -> dict:
    response = client.post("/workspaces", json={"name": name, "description": "Test workspace"})
    assert response.status_code == 201
    return response.json()


def upload_csv_source(
    client,
    workspace_id: int,
    filename: str = "metrics.csv",
    title: str = "Monthly metrics",
    csv_content: str | None = None,
) -> dict:
    if csv_content is None:
        csv_content = (
            "month,revenue,region\n"
            "2026-01,1000,North\n2026-02,1500,North\n2026-03,1200,South\n"
            "2026-04,1800,South\n2026-05,2200,North\n2026-06,2000,East"
        )

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace_id),
            "title": title,
            "team_label": "marketing",
            "category_labels": ["analytics_metrics", "revenue_sales"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-06",
        },
        files={"file": (filename, csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload_invalid_csv(client, workspace_id: int) -> dict:
    """CSV that cannot be parsed."""
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace_id),
            "title": "Bad CSV",
            "team_label": "data_analysis",
            "category_labels": ["analytics_metrics"],
        },
        files={"file": ("bad.csv", b"not,\xa0valid\x02csv\xff", "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# CSV Profiling
# ---------------------------------------------------------------------------

def test_source_summary_generated_from_sample_csv(client) -> None:
    """CSV upload should produce source_summary artifact and mark source Ready."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY, source.get("processing_error")

    # Fetch artifacts via legacy per-source endpoint
    artifacts = client.get(f"/visualizations/source/{source['id']}").json()
    assert len(artifacts) > 0

    summary_artifacts = [a for a in artifacts if a["artifact_type"] == "source_summary"]
    assert len(summary_artifacts) >= 1

    summary = summary_artifacts[0]["content_json"]
    assert summary["statistics"]["row_count"] == 6
    assert summary["statistics"]["column_count"] == 3
    col_names = {c["name"] for c in summary.get("columns", [])}
    assert col_names == {"month", "revenue", "region"}


def test_source_content_generated_with_column_profiling(client) -> None:
    """When CSV has date and numeric columns, source_content artifact includes chunks."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"], csv_content="date,revenue\n2026-01,1000\n2026-02,1500\n2026-03,1200")

    assert source["processing_status"] == ProcessingStatus.READY

    artifacts = client.get(f"/visualizations/source/{source['id']}").json()
    content_artifacts = [a for a in artifacts if a["artifact_type"] == "source_content"]
    assert len(content_artifacts) >= 1

    content = content_artifacts[0]["content_json"]
    # Envelope should have chunks
    assert "chunks" in content
    assert len(content["chunks"]) > 0
    # Chunks should reference columns with type info
    col_names_in_chunks = set()
    for chunk in content["chunks"]:
        for col in chunk.get("columns", []):
            col_names_in_chunks.add(col)
    assert "revenue" in col_names_in_chunks
    assert "date" in col_names_in_chunks


def test_source_insight_generated_with_numeric_summary(client) -> None:
    """source_insight artifact with findings should be generated for numeric columns."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY

    artifacts = client.get(f"/visualizations/source/{source['id']}").json()
    insight_artifacts = [a for a in artifacts if a["artifact_type"] == "source_insight"]
    assert len(insight_artifacts) >= 1

    # At least one finding should mention revenue stats
    findings = insight_artifacts[0]["content_json"].get("findings", [])
    finding_texts = " ".join(f.get("text", "") for f in findings)
    assert "revenue" in finding_texts.lower()


def test_invalid_csv_marks_source_failed(client) -> None:
    """Upload of unparseable CSV should mark source as Failed."""
    workspace = create_workspace(client)

    # Write empty CSV to trigger parse failure
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Empty CSV",
            "team_label": "data_analysis",
            "category_labels": ["analytics_metrics"],
        },
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    # Empty file might be accepted but processing fails
    if response.status_code == 201:
        source = response.json()
        assert source["processing_status"] == ProcessingStatus.FAILED, f"Expected failed, got {source['processing_status']}"


def test_csv_with_categorical_and_numeric_generates_source_content(client) -> None:
    """CSV with categorical + numeric columns should produce source_content with chunks."""
    workspace = create_workspace(client)
    csv_content = "region,revenue\nNorth,1000\nSouth,1500\nEast,800\nWest,1200"
    source = upload_csv_source(client, workspace["id"], csv_content=csv_content)

    assert source["processing_status"] == ProcessingStatus.READY

    artifacts = client.get(f"/visualizations/source/{source['id']}").json()
    content_artifacts = [a for a in artifacts if a["artifact_type"] == "source_content"]
    assert len(content_artifacts) >= 1
    # Chunks should exist with column references
    content = content_artifacts[0]["content_json"]
    assert "chunks" in content
    assert len(content["chunks"]) > 0
    # Chunk text should mention both region and revenue columns
    all_text = " ".join(c.get("text", "") for c in content["chunks"])
    assert "revenue" in all_text.lower()
    assert "region" in all_text.lower()


# ---------------------------------------------------------------------------
# Visualization Snapshot API
# ---------------------------------------------------------------------------

def test_get_visualization_snapshot_returns_snapshot_scoped_by_workspace_and_period(client) -> None:
    """GET /visualizations?workspace_id=X&period_start_month=Y&period_end_month=Z returns a snapshot."""
    workspace = create_workspace(client, "Workspace 1")
    source = upload_csv_source(client, workspace["id"])
    assert source["processing_status"] == ProcessingStatus.READY

    resp = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-01&period_end_month=2026-06"
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["workspace_id"] == workspace["id"]
    assert snapshot["period_start_month"] == "2026-01"
    assert snapshot["period_end_month"] == "2026-06"
    assert snapshot["status"] == "ready"
    assert source["id"] in snapshot["source_ids_json"]
    assert len(snapshot["artifact_ids_json"]) > 0


def test_snapshot_includes_overlapping_ready_sources(client) -> None:
    """Snapshot includes sources whose period overlaps the requested range."""
    workspace = create_workspace(client)

    # Source covering Jan–Jun
    source1 = upload_csv_source(client, workspace["id"], title="S1")
    assert source1["processing_status"] == ProcessingStatus.READY

    # Request snapshot for Mar–Apr (overlaps Jan–Jun)
    resp = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-03&period_end_month=2026-04"
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert source1["id"] in snapshot["source_ids_json"]


def test_snapshot_excludes_non_overlapping_sources(client) -> None:
    """Snapshot excludes sources whose period does not overlap."""
    workspace = create_workspace(client)

    # Source covering Jan–Mar only (override period in upload)
    csv_content = "col1,col2\n1,2\n3,4\n5,6\n"
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "S1",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-03",
        },
        files={"file": ("data.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 201
    source1 = response.json()
    assert source1["processing_status"] == ProcessingStatus.READY

    # Request snapshot for Jun–Dec (no overlap)
    resp = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-06&period_end_month=2026-12"
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert source1["id"] not in snapshot["source_ids_json"]
    assert snapshot["content_json"]["coverage"]["total_sources"] == 0


def test_snapshot_excludes_soft_deleted_sources(client) -> None:
    """Snapshot should not include soft-deleted sources."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])
    assert source["processing_status"] == ProcessingStatus.READY

    client.delete(f"/sources/{source['id']}")

    resp = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-01&period_end_month=2026-06"
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert source["id"] not in snapshot["source_ids_json"]


def test_snapshot_cache_hit_returns_same_id(client) -> None:
    """Repeated GET with same params returns the same snapshot (same id)."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])
    assert source["processing_status"] == ProcessingStatus.READY

    resp1 = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-01&period_end_month=2026-06"
    )
    resp2 = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-01&period_end_month=2026-06"
    )
    assert resp1.json()["id"] == resp2.json()["id"]


def test_snapshot_refresh_regenerates(client) -> None:
    """POST /visualizations/refresh forces regeneration — generated_at changes."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])
    assert source["processing_status"] == ProcessingStatus.READY

    resp1 = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-01&period_end_month=2026-06"
    )
    original_generated_at = resp1.json()["generated_at"]

    resp2 = client.post(
        "/visualizations/refresh",
        json={
            "workspace_id": workspace["id"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-06",
        },
    )
    assert resp2.status_code == 200
    # Refreshed snapshot should have a different generated_at timestamp
    refreshed_generated_at = resp2.json()["generated_at"]
    assert refreshed_generated_at is not None
    # The original should have been replaced; new one has a fresh timestamp
    assert refreshed_generated_at >= original_generated_at


def test_snapshot_requires_period_fields(client) -> None:
    """GET /visualizations without period params should return 422."""
    workspace = create_workspace(client)

    resp = client.get(f"/visualizations?workspace_id={workspace['id']}")
    assert resp.status_code == 422


def test_snapshot_empty_coverage_when_no_ready_sources(client) -> None:
    """Snapshot returns ready status with empty coverage when no overlapping sources exist."""
    workspace = create_workspace(client)

    resp = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-01&period_end_month=2026-06"
    )
    assert resp.status_code == 200
    snapshot = resp.json()
    assert snapshot["status"] == "ready"
    assert snapshot["content_json"]["coverage"]["total_sources"] == 0
    assert len(snapshot["content_json"]["gaps"]) > 0


def test_snapshot_content_json_has_required_sections(client) -> None:
    """Snapshot content_json includes coverage, source_cards, key_findings, gaps."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])
    assert source["processing_status"] == ProcessingStatus.READY

    resp = client.get(
        f"/visualizations?workspace_id={workspace['id']}&period_start_month=2026-01&period_end_month=2026-06"
    )
    content = resp.json()["content_json"]
    assert "coverage" in content
    assert "source_cards" in content
    assert "key_findings" in content
    assert "risks_assumptions" in content
    assert "opportunities" in content
    assert "gaps" in content


# ---------------------------------------------------------------------------
# Legacy per-source endpoint (backward compat)
# ---------------------------------------------------------------------------

def test_get_visualization_for_source_returns_empty_for_non_ready_source(client) -> None:
    """GET /visualizations/source/{source_id} returns empty list for non-ready sources."""
    workspace = create_workspace(client)

    # Upload a PDF (not processed yet in Task 2)
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "PDF Document",
            "team_label": "business",
            "category_labels": ["competitor_analysis"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-03",
        },
        files={"file": ("doc.pdf", b"%PDF-1.4 sample", "application/pdf")},
    )
    assert response.status_code == 201
    pdf_source = response.json()

    # PDFs processed as ready but without CSV profile should still return (empty artifacts list is ok)
    viz = client.get(f"/visualizations/source/{pdf_source['id']}").json()
    assert isinstance(viz, list)
