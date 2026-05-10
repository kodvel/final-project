from enum import StrEnum


class TeamLabel(StrEnum):
    MARKETING = "marketing"
    PRODUCT = "product"
    DATA_ANALYSIS = "data_analysis"
    BUSINESS = "business"


class CategoryLabel(StrEnum):
    ANALYTICS_METRICS = "analytics_metrics"
    MARKET_RESEARCH = "market_research"
    PRODUCT_FEATURE = "product_feature"
    CUSTOMER_INSIGHT = "customer_insight"
    BUSINESS_MODEL = "business_model"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    REVENUE_SALES = "revenue_sales"


class SourceFileType(StrEnum):
    CSV = "csv"
    PDF = "pdf"


class ProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ChatMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageType(StrEnum):
    NORMAL = "normal"
    DECISION_BRIEF = "decision_brief"
    COMMAND_RESULT = "command_result"


class DecisionRecommendationStatus(StrEnum):
    GO = "go"
    NO_GO = "no_go"
    VALIDATE_FIRST = "validate_first"


class DecisionApprovalStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArtifactType(StrEnum):
    CSV_PROFILE = "csv_profile"
    CHART_SPEC = "chart_spec"
    INSIGHT_CARD = "insight_card"
    PDF_SUMMARY = "pdf_summary"
    PDF_INSIGHT_BOARD = "pdf_insight_board"
