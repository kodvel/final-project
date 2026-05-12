from app.models.enums import ProcessingStatus
from app.services.sources import get_source_for_audit


def create_workspace(client, name: str = "Demo") -> dict:
    response = client.post("/workspaces", json={"name": name, "description": "Test workspace"})
    assert response.status_code == 201
    return response.json()


def upload_source(client, workspace_id: int, filename: str = "metrics.csv", title: str = "Monthly metrics") -> dict:
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace_id),
            "title": title,
            "team_label": "marketing",
            "category_labels": ["analytics_metrics", "revenue_sales"],
            "period_start_month": "2026-04",
            "period_end_month": "2026-04",
        },
        files={"file": (filename, b"month,revenue\n2026-04,100\n", "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload_invalid_csv(client, workspace_id: int) -> dict:
    """CSV that cannot be parsed (empty content triggers failure)."""
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace_id),
            "title": "Bad CSV",
            "team_label": "data_analysis",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-01",
        },
        files={"file": ("bad.csv", b"", "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_workspaces(client) -> None:
    created = create_workspace(client, "Developer 1")

    response = client.get("/workspaces")

    assert response.status_code == 200
    assert any(workspace["id"] == created["id"] for workspace in response.json())


def test_upload_csv_source_saves_metadata_and_file(client) -> None:
    workspace = create_workspace(client)

    source = upload_source(client, workspace["id"])

    assert source["workspace_id"] == workspace["id"]
    assert source["file_type"] == "csv"
    assert source["category_labels"] == ["analytics_metrics", "revenue_sales"]
    # Valid CSV is processed synchronously/fallback and marked READY with artifacts
    assert source["processing_status"] == ProcessingStatus.READY
    assert source["storage_path"].endswith(f"uploads/{workspace['id']}/{source['id']}/original.csv")


def test_upload_pdf_source(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Competitor brief",
            "team_label": "business",
            "category_labels": ["competitor_analysis"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-03",
        },
        files={"file": ("brief.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["file_type"] == "pdf"


def test_reject_unsupported_file_type(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={"workspace_id": str(workspace["id"]), "title": "Notes", "team_label": "product", "category_labels": ["product_feature"]},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422


def test_sources_are_scoped_by_workspace(client) -> None:
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")
    source = upload_source(client, first["id"], title="A source")
    upload_source(client, second["id"], title="B source")

    response = client.get(f"/sources?workspace_id={first['id']}")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [source["id"]]


def test_soft_delete_hides_source_but_keeps_audit_access(client) -> None:
    workspace = create_workspace(client)
    source = upload_source(client, workspace["id"])

    delete_response = client.delete(f"/sources/{source['id']}")
    list_response = client.get(f"/sources?workspace_id={workspace['id']}")

    assert delete_response.status_code == 204
    assert list_response.json() == []

    override = next(iter(client.app.dependency_overrides.values()))
    session = next(override())
    try:
        audit_source = get_source_for_audit(session, source["id"])
        assert audit_source is not None
        assert audit_source.deleted_at is not None
    finally:
        session.close()


def test_retry_processing_for_failed_source(client) -> None:
    workspace = create_workspace(client)

    # Upload an invalid/unparseable CSV that will fail processing
    bad_source = upload_invalid_csv(client, workspace["id"])

    # Initially the source should be FAILED due to parse error
    assert bad_source["processing_status"] == ProcessingStatus.FAILED
    assert bad_source["processing_error"]

    # Retry should re-run processing (and fail again for truly invalid content)
    response = client.post(f"/sources/{bad_source['id']}/retry-processing")

    assert response.status_code == 200
    # Retry of invalid content still fails (no artifacts can be generated)
    assert response.json()["processing_status"] == "failed"


def test_get_deleted_source_returns_404(client) -> None:
    workspace = create_workspace(client)
    source = upload_source(client, workspace["id"])

    client.delete(f"/sources/{source['id']}")
    response = client.get(f"/sources/{source['id']}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Period month validation tests
# ---------------------------------------------------------------------------


def test_source_with_valid_period_months(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Quarterly metrics",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-01",
            "period_end_month": "2026-03",
        },
        files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["period_start_month"] == "2026-01"
    assert data["period_end_month"] == "2026-03"
    assert data["period_label"] == "January – March 2026"


def test_source_derives_period_label_single_month(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Single month",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-04",
            "period_end_month": "2026-04",
        },
        files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["period_label"] == "April 2026"


def test_source_rejects_invalid_month_format(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Bad month",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-13",
            "period_end_month": "2026-12",
        },
        files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
    )

    assert response.status_code == 422
    assert "period_start_month" in response.json()["detail"]


def test_source_rejects_invalid_month_text(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Bad month text",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "not-a-month",
        },
        files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
    )

    assert response.status_code == 422


def test_source_rejects_start_after_end(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "Reversed period",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
            "period_start_month": "2026-06",
            "period_end_month": "2026-01",
        },
        files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
    )

    assert response.status_code == 422
    assert "must be <=" in response.json()["detail"]


def test_source_without_period_is_rejected(client) -> None:
    workspace = create_workspace(client)

    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace["id"]),
            "title": "No period",
            "team_label": "marketing",
            "category_labels": ["analytics_metrics"],
        },
        files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
    )

    assert response.status_code == 422
