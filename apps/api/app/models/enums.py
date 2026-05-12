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
    SOURCE_SUMMARY = "source_summary"
    SOURCE_CONTENT = "source_content"
    SOURCE_INSIGHT = "source_insight"


class MessageStatus(StrEnum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class CitationType(StrEnum):
    UPLOADED_SOURCE = "uploaded_source"
    WEB = "web"


class CitationStatus(StrEnum):
    AVAILABLE = "available"
    SOURCE_DELETED = "source_deleted"
    SOURCE_FAILED = "source_failed"
    ARTIFACT_MISSING = "artifact_missing"
    WEB_UNAVAILABLE = "web_unavailable"
