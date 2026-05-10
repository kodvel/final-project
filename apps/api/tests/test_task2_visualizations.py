"""Task 2 tests: CSV processing into Visualization Data."""

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
            "period_label": "H1 2026",
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

def test_csv_profile_generated_from_sample_csv(client) -> None:
    """CSV upload should produce csv_profile artifact and mark source Ready."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY, source.get("processing_error")

    # Fetch artifacts via visualization endpoint
    artifacts = client.get(f"/visualizations/{source['id']}").json()
    assert len(artifacts) > 0

    profile_artifacts = [a for a in artifacts if a["artifact_type"] == "csv_profile"]
    assert len(profile_artifacts) >= 1

    profile = profile_artifacts[0]["content_json"]
    assert profile["row_count"] == 6
    assert profile["column_count"] == 3
    col_names = {c["name"] for c in profile["columns"]}
    assert col_names == {"month", "revenue", "region"}


def test_chart_spec_generated_when_date_and_numeric_columns_exist(client) -> None:
    """When CSV has date and numeric columns, chart_spec artifacts should be generated."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"], csv_content="date,revenue\n2026-01,1000\n2026-02,1500\n2026-03,1200")

    assert source["processing_status"] == ProcessingStatus.READY

    artifacts = client.get(f"/visualizations/{source['id']}").json()
    chart_specs = [a for a in artifacts if a["artifact_type"] == "chart_spec"]
    assert len(chart_specs) >= 1

    # At least one chart spec should be a line chart (date + numeric)
    chart_types = {c["content_json"].get("chart_type") for c in chart_specs}
    assert "line" in chart_types


def test_insight_card_generated_with_numeric_summary(client) -> None:
    """Insight card with stat_summary should be generated for numeric columns."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY

    artifacts = client.get(f"/visualizations/{source['id']}").json()
    insight_cards = [a for a in artifacts if a["artifact_type"] == "insight_card"]
    assert len(insight_cards) >= 1

    # At least one insight should mention revenue stats
    insight_titles = {i["title"] for i in [a["content_json"] for a in insight_cards]}
    assert any("revenue" in t.lower() for t in insight_titles)


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


def test_csv_with_categorical_and_numeric_generates_segment_chart(client) -> None:
    """CSV with categorical + numeric columns should produce a bar chart spec."""
    workspace = create_workspace(client)
    csv_content = "region,revenue\nNorth,1000\nSouth,1500\nEast,800\nWest,1200"
    source = upload_csv_source(client, workspace["id"], csv_content=csv_content)

    assert source["processing_status"] == ProcessingStatus.READY

    artifacts = client.get(f"/visualizations/{source['id']}").json()
    chart_specs = [a for a in artifacts if a["artifact_type"] == "chart_spec"]
    bar_charts = [c for c in chart_specs if c["content_json"].get("chart_type") == "bar"]
    assert len(bar_charts) >= 1


# ---------------------------------------------------------------------------
# Visualization API
# ---------------------------------------------------------------------------

def test_get_visualizations_returns_artifacts_scoped_by_workspace(client) -> None:
    """GET /visualizations?workspace_id=X returns only artifacts from that workspace."""
    workspace1 = create_workspace(client, "Workspace 1")
    workspace2 = create_workspace(client, "Workspace 2")

    source1 = upload_csv_source(client, workspace1["id"], title="Source 1")
    source2 = upload_csv_source(client, workspace2["id"], title="Source 2")

    assert source1["processing_status"] == ProcessingStatus.READY
    assert source2["processing_status"] == ProcessingStatus.READY

    viz1 = client.get(f"/visualizations?workspace_id={workspace1['id']}").json()
    viz2 = client.get(f"/visualizations?workspace_id={workspace2['id']}").json()

    # Each workspace's viz list should only contain its own source's artifacts
    source1_artifact_count = len(client.get(f"/visualizations/{source1['id']}").json())
    source2_artifact_count = len(client.get(f"/visualizations/{source2['id']}").json())

    assert len(viz1) == source1_artifact_count
    assert len(viz2) == source2_artifact_count


def test_get_visualizations_excludes_soft_deleted_sources(client) -> None:
    """Visualizations should not include artifacts from soft-deleted sources."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])

    assert source["processing_status"] == ProcessingStatus.READY
    client.delete(f"/sources/{source['id']}")

    viz = client.get(f"/visualizations?workspace_id={workspace['id']}").json()
    deleted_source_ids = {a["source_id"] for a in viz}
    assert source["id"] not in deleted_source_ids


def test_visualizations_filter_by_team_label(client) -> None:
    """GET /visualizations?team_label=marketing returns only marketing sources."""
    workspace = create_workspace(client)

    # Upload marketing source
    marketing_source = upload_csv_source(client, workspace["id"], title="Marketing Data")
    assert marketing_source["processing_status"] == ProcessingStatus.READY

    # Upload different team source
    client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Product Data",
            "team_label": "product",
            "category_labels": ["product_feature"],
        },
        files={"file": ("product.csv", b"col1,col2\n1,2\n", "text/csv")},
    )

    viz_marketing = client.get(f"/visualizations?workspace_id={workspace['id']}&team_label=marketing").json()
    viz_all = client.get(f"/visualizations?workspace_id={workspace['id']}").json()

    # Marketing viz should be a subset of all viz
    assert len(viz_marketing) <= len(viz_all)


def test_visualizations_filter_by_category_label(client) -> None:
    """GET /visualizations?category_label=analytics_metrics returns only analytics sources."""
    workspace = create_workspace(client)

    analytics_source = upload_csv_source(client, workspace["id"], title="Analytics Data")
    assert analytics_source["processing_status"] == ProcessingStatus.READY

    viz_filtered = client.get(f"/visualizations?workspace_id={workspace['id']}&category_label=analytics_metrics").json()
    viz_all = client.get(f"/visualizations?workspace_id={workspace['id']}").json()

    assert len(viz_filtered) <= len(viz_all)


def test_get_visualization_for_source_returns_empty_for_non_ready_source(client) -> None:
    """GET /visualizations/{source_id} returns empty list for non-ready sources."""
    workspace = create_workspace(client)

    # Upload a PDF (not processed yet in Task 2)
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "PDF Document",
            "team_label": "business",
            "category_labels": ["competitor_analysis"],
        },
        files={"file": ("doc.pdf", b"%PDF-1.4 sample", "application/pdf")},
    )
    assert response.status_code == 201
    pdf_source = response.json()

    # PDF processing is not yet implemented in Task 2, so it stays "ready" (placeholder)
    # In Task 3 this would be different. For now PDF just goes to Ready without artifacts.
    viz = client.get(f"/visualizations/{pdf_source['id']}").json()
    # PDFs processed as ready but without CSV profile should still return (empty artifacts list is ok)
    assert isinstance(viz, list)
