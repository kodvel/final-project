"""Task 10 tests: API contract alignment between backend schemas and frontend types."""

from app.models.enums import (
    ArtifactType,
    CategoryLabel,
    ChatMessageRole,
    ChatMessageType,
    DecisionApprovalStatus,
    DecisionRecommendationStatus,
    ProcessingStatus,
    SourceFileType,
    TeamLabel,
)
from app.schemas.decision_brief import DecisionBriefRead
from app.schemas.visualization import VisualizationArtifactRead

# ---------------------------------------------------------------------------
# Enum wire value tests
# These ensure the string values sent over JSON match what the frontend expects.
# ---------------------------------------------------------------------------

def test_processing_status_wire_values() -> None:
    assert ProcessingStatus.UPLOADED == "uploaded"
    assert ProcessingStatus.PROCESSING == "processing"
    assert ProcessingStatus.READY == "ready"
    assert ProcessingStatus.FAILED == "failed"
    assert set(ProcessingStatus) == {"uploaded", "processing", "ready", "failed"}


def test_team_label_wire_values() -> None:
    assert TeamLabel.MARKETING == "marketing"
    assert TeamLabel.PRODUCT == "product"
    assert TeamLabel.DATA_ANALYSIS == "data_analysis"
    assert TeamLabel.BUSINESS == "business"
    assert set(TeamLabel) == {"marketing", "product", "data_analysis", "business"}


def test_category_label_wire_values() -> None:
    expected = {
        "analytics_metrics",
        "market_research",
        "product_feature",
        "customer_insight",
        "business_model",
        "competitor_analysis",
        "revenue_sales",
    }
    assert set(CategoryLabel) == expected


def test_source_file_type_wire_values() -> None:
    assert SourceFileType.CSV == "csv"
    assert SourceFileType.PDF == "pdf"
    assert set(SourceFileType) == {"csv", "pdf"}


def test_artifact_type_wire_values() -> None:
    assert ArtifactType.CSV_PROFILE == "csv_profile"
    assert ArtifactType.CHART_SPEC == "chart_spec"
    assert ArtifactType.INSIGHT_CARD == "insight_card"
    assert ArtifactType.SOURCE_SUMMARY == "source_summary"
    assert ArtifactType.SOURCE_INSIGHT == "source_insight"
    assert set(ArtifactType) == {
        "csv_profile", "chart_spec", "insight_card", "source_summary", "source_insight"
    }


def test_chat_message_role_wire_values() -> None:
    assert ChatMessageRole.USER == "user"
    assert ChatMessageRole.ASSISTANT == "assistant"
    assert ChatMessageRole.SYSTEM == "system"
    assert set(ChatMessageRole) == {"user", "assistant", "system"}


def test_chat_message_type_wire_values() -> None:
    assert ChatMessageType.NORMAL == "normal"
    assert ChatMessageType.DECISION_BRIEF == "decision_brief"
    assert ChatMessageType.COMMAND_RESULT == "command_result"
    assert set(ChatMessageType) == {"normal", "decision_brief", "command_result"}


def test_decision_recommendation_status_wire_values() -> None:
    assert DecisionRecommendationStatus.GO == "go"
    assert DecisionRecommendationStatus.NO_GO == "no_go"
    assert DecisionRecommendationStatus.VALIDATE_FIRST == "validate_first"
    assert set(DecisionRecommendationStatus) == {"go", "no_go", "validate_first"}


def test_decision_approval_status_wire_values() -> None:
    assert DecisionApprovalStatus.DRAFT == "draft"
    assert DecisionApprovalStatus.REVIEWED == "reviewed"
    assert DecisionApprovalStatus.APPROVED == "approved"
    assert DecisionApprovalStatus.REJECTED == "rejected"
    assert set(DecisionApprovalStatus) == {"draft", "reviewed", "approved", "rejected"}


# ---------------------------------------------------------------------------
# Schema field completeness tests
# These ensure response schemas include all fields the frontend type expects.
# ---------------------------------------------------------------------------

def test_decision_brief_read_has_all_required_fields() -> None:
    fields = set(DecisionBriefRead.model_fields.keys())
    required = {
        "id",
        "workspace_id",
        "chat_session_id",
        "chat_message_id",
        "title",
        "recommendation_status",
        "approval_status",
        "content_json",
        "created_at",
        "updated_at",
    }
    assert required.issubset(fields), f"Missing fields: {required - fields}"


def test_visualization_artifact_read_has_source_metadata_fields() -> None:
    fields = set(VisualizationArtifactRead.model_fields.keys())
    required = {"id", "source_id", "artifact_type", "title", "content_json"}
    source_metadata = {"source_title", "source_file_type", "team_label", "category_labels"}
    assert required.issubset(fields), f"Missing core fields: {required - fields}"
    assert source_metadata.issubset(fields), f"Missing source metadata fields: {source_metadata - fields}"


# ---------------------------------------------------------------------------
# API response shape tests
# These verify the actual HTTP response includes the expected fields.
# ---------------------------------------------------------------------------

def create_workspace(client, name: str = "Demo") -> dict:
    response = client.post("/workspaces", json={"name": name})
    assert response.status_code == 201
    return response.json()


def upload_csv_source(client, workspace_id: int) -> dict:
    csv_content = "month,revenue\n2026-01,1000\n2026-02,1500\n"
    response = client.post(
        "/sources",
        data={
            "workspace_id": str(workspace_id),
            "title": "Contract Test Source",
            "team_label": "product",
            "category_labels": ["product_feature"],
            "period_label": "Q1 2026",
        },
        files={"file": ("data.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_source_response_shape(client) -> None:
    """GET /sources returns all fields the frontend SourceDataApi type expects."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])

    expected_keys = {
        "id", "workspace_id", "title", "team_label", "category_labels",
        "file_type", "processing_status", "original_filename", "storage_path",
        "uploaded_at",
    }
    assert expected_keys.issubset(source.keys()), f"Missing keys: {expected_keys - source.keys()}"


def test_workspace_response_has_required_timestamps(client) -> None:
    """GET /workspaces returns created_at and updated_at (both required, not optional)."""
    workspace = create_workspace(client)
    assert "created_at" in workspace
    assert "updated_at" in workspace
    assert workspace["created_at"] is not None
    assert workspace["updated_at"] is not None


def test_visualization_response_includes_source_metadata(client) -> None:
    """GET /visualizations/{source_id} returns source metadata alongside artifact data."""
    workspace = create_workspace(client)
    source = upload_csv_source(client, workspace["id"])

    assert source["processing_status"] == "ready", source.get("processing_error")

    artifacts = client.get(f"/visualizations/{source['id']}").json()
    assert len(artifacts) > 0

    for artifact in artifacts:
        assert artifact["source_title"] == "Contract Test Source"
        assert artifact["source_file_type"] == "csv"
        assert artifact["team_label"] == "product"
        assert "product_feature" in artifact["category_labels"]


def test_visualization_list_response_includes_source_metadata(client) -> None:
    """GET /visualizations?workspace_id=X returns source metadata on each artifact."""
    workspace = create_workspace(client)
    upload_csv_source(client, workspace["id"])

    artifacts = client.get(f"/visualizations?workspace_id={workspace['id']}").json()
    assert len(artifacts) > 0

    for artifact in artifacts:
        assert artifact["source_title"] is not None
        assert artifact["team_label"] == "product"
        assert artifact["category_labels"] is not None


def test_openapi_schema_exposes_all_enums(client) -> None:
    """OpenAPI spec includes enum schemas for all active routes.

    DecisionRecommendationStatus and DecisionApprovalStatus are excluded here
    because the /decision-briefs route has no endpoints yet (Task 8). They will
    appear in the spec automatically once Task 8 adds response endpoints.
    """
    openapi = client.get("/openapi.json").json()
    schemas = openapi.get("components", {}).get("schemas", {})

    active_enums = {
        "ProcessingStatus",
        "TeamLabel",
        "CategoryLabel",
        "SourceFileType",
        "ArtifactType",
        "ChatMessageRole",
        "ChatMessageType",
    }
    missing = active_enums - set(schemas.keys())
    assert not missing, f"Missing enum schemas in OpenAPI spec: {missing}"
