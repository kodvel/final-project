# PRD: Company Intelligence Copilot

## Problem Statement

Companies often collect product, marketing, data analysis, and business information in separate places. Marketing may own user behavior reports, product teams may own feature and roadmap documents, data analysts may prepare monthly datasets, and business teams may own market, competitor, revenue, and business model documents.

Because those sources are fragmented, teams struggle to turn company knowledge into product decisions. A founder, product lead, or business team member may need to ask: “What changed this month?”, “What source supports this recommendation?”, “Which feature should we build next?”, “What are the risks?”, or “Can this become a decision brief?” Today, answering those questions requires manual review across spreadsheets, PDFs, analytics exports, and stakeholder notes.

For the final project MVP, the team needs a focused web app that demonstrates a strong AI use case without overbuilding a full enterprise platform. The app should show how source data can become a company knowledge base, how AI can reason over that knowledge, and how users can discuss strategy with an AI consultant grounded in uploaded sources.

## Solution

Company Intelligence Copilot is a chat-first company intelligence workspace. It lets a user upload monthly company source data, label that data by team, category, and period, visualize structured data automatically, summarize unstructured documents, and discuss all available sources with an AI Company Strategy Consultant.

The MVP has three main navigation items:

- Chat
- Visualization Data
- Source Data

The Chat page behaves like a GPT-style strategy workspace. The AI is not only a passive assistant. It acts as a Company Strategy Consultant that can analyze source data, challenge assumptions, compare options, recommend product or feature initiatives, identify risks, and generate a formatted Decision Brief inside the chat when asked.

The Visualization Data page turns uploaded sources into understandable artifacts. CSV files produce an auto-generated visual story, including summary cards, trends, segment breakdowns, relationship views, anomaly highlights, and insight cards. PDF files produce a Document Insight view from generic Source Artifacts, including summaries, key findings, assumptions, risks, opportunities, and source quotes.

The Source Data page is the Single Source of Truth for uploaded company context. Users can add CSV and PDF files, choose team labels, choose one or more category labels, set the period, and track processing status. CSV files are parsed for visualization and analysis. PDF files are OCRed, chunked, labeled, and later indexed for retrieval.

The backend uses FastAPI as the API layer, Python for AI/RAG/data processing, SQLModel and Alembic for relational app data, ChromaDB as the vector database for PDF/document retrieval, optional Redis and Celery for background file processing, OpenAI Agent SDK for agent orchestration, and Langfuse for agent observability. The frontend uses TanStack Start, TanStack Router, React, and TypeScript.

## User Stories

1. As a founder, I want to upload company source data, so that the AI can understand my company context.
2. As a founder, I want to ask strategic questions in chat, so that I can discuss product and business decisions with an AI consultant.
3. As a founder, I want AI answers to reference source data, so that I can trust the recommendation.
4. As a founder, I want the AI to challenge assumptions, so that I do not blindly follow weak ideas.
5. As a founder, I want the AI to highlight missing data, so that I know what information is needed before making a decision.
6. As a founder, I want to generate a Decision Brief in chat, so that I can turn discussion into a shareable decision artifact.
7. As a product team member, I want to upload product and feature documents, so that the AI can understand current delivered features and product direction.
8. As a product team member, I want to ask which feature should be prioritized, so that I can evaluate decisions using available evidence.
9. As a product team member, I want to compare multiple product initiatives, so that I can understand trade-offs.
10. As a product team member, I want to ask the AI to identify risks in a feature idea, so that I can validate before building.
11. As a product team member, I want the AI to connect product information with business and market context, so that feature decisions are not based only on internal opinion.
12. As a product team member, I want a Decision Brief to include success metrics, so that the team knows how to evaluate whether a decision works.
13. As a product team member, I want a Decision Brief to include Go, No-Go, or Validate First status, so that next steps are explicit.
14. As a marketing team member, I want to upload user behavior or campaign analytics exports, so that marketing signals become part of company intelligence.
15. As a marketing team member, I want structured CSV data to be visualized automatically, so that I do not need to manually create charts for every upload.
16. As a marketing team member, I want the AI to find trends and anomalies from uploaded data, so that unusual performance changes are easier to notice.
17. As a marketing team member, I want the AI to explain changes in plain language, so that non-technical stakeholders can understand the data.
18. As a data analyst, I want to upload prepared CSV datasets, so that the app can visualize and analyze monthly source data.
19. As a data analyst, I want uploaded datasets to have clear labels and periods, so that the AI can use the right data for the right question.
20. As a data analyst, I want file processing status, so that I know whether the source is ready for analysis.
21. As a data analyst, I want failed processing states to be visible, so that I can retry or replace invalid files.
22. As a business team member, I want to upload market research PDFs, so that the AI can use market evidence in strategic discussion.
23. As a business team member, I want to upload competitor analysis PDFs, so that feature recommendations can consider external market positioning.
24. As a business team member, I want to upload business model documents, so that the AI can understand assumptions behind the company strategy.
25. As a business team member, I want PDF documents to become insight boards, so that long documents are easier to review.
26. As a business team member, I want PDF insight boards to show assumptions and risks, so that hidden business constraints are easier to identify.
27. As a business team member, I want source quotes from PDFs, so that AI summaries can be checked against the original document.
28. As a user, I want to classify a source by team label, so that source ownership remains clear.
29. As a user, I want to classify a source by category label, so that source purpose remains clear.
30. As a user, I want category labels to support multi-select, so that one source can represent more than one kind of company knowledge.
31. As a user, I want to assign a period to each source, so that monthly and range-based questions have context.
32. As a user, I want to filter Visualization Data by team, so that I can focus on sources from a specific function.
33. As a user, I want to filter Visualization Data by category, so that I can inspect a specific type of company knowledge.
34. As a user, I want to filter Visualization Data by period, so that I can inspect data for a specific month or range.
35. As a user, I want CSV files to produce executive summary cards, so that the most important metrics are visible quickly.
36. As a user, I want CSV files to produce trend visualizations when time columns exist, so that changes over time are easy to see.
37. As a user, I want CSV files to produce segment breakdowns when category columns exist, so that performance differences across groups are visible.
38. As a user, I want CSV files to produce relationship views when numeric columns exist, so that possible correlations can be explored.
39. As a user, I want CSV files to produce anomaly highlights, so that spikes, drops, or outliers are easy to identify.
40. As a user, I want CSV files to produce auto insight cards, so that charts are explained in plain language.
41. As a user, I want PDF files to produce document summaries, so that I can understand the document quickly.
42. As a user, I want PDF files to produce key findings, so that important points are surfaced.
43. As a user, I want PDF files to produce assumptions, so that the AI can reason about business or market beliefs.
44. As a user, I want PDF files to produce risks, so that potential issues are visible before decisions are made.
45. As a user, I want PDF files to produce opportunities, so that possible product or business initiatives can be identified.
46. As a user, I want PDF files to include source quotes, so that insight boards remain grounded in the document.
47. As a user, I want the AI to auto-select relevant sources in chat, so that I do not need to manually configure every prompt.
48. As a user, I want to override source scope in chat, so that I can ask questions about a specific team, category, or period.
49. As a user, I want chat responses to show which sources were used, so that I understand the basis of the answer.
50. As a user, I want chat responses to show a Langfuse trace link, so that AI behavior is observable during the demo.
51. As a user, I want chat responses to be semi-structured, so that strategic answers are easy to scan.
52. As a user, I want chat responses to include a direct answer, so that I can quickly understand the conclusion.
53. As a user, I want chat responses to include evidence, so that recommendations are grounded.
54. As a user, I want chat responses to include interpretation, so that I understand strategic meaning.
55. As a user, I want chat responses to include recommendations or next steps, so that discussion becomes actionable.
56. As a user, I want chat responses to include confidence and gaps, so that I understand uncertainty.
57. As a user, I want the AI to state when data is insufficient, so that it does not hallucinate certainty.
58. As a user, I want the AI to label assumptions, so that unsupported claims are clear.
59. As a user, I want the AI to highlight contradictions between sources, so that the team can resolve conflicting evidence.
60. As a user, I want Decision Briefs to be generated as formatted chat responses, so that the MVP stays simple without a separate brief management workflow.
61. As a user, I want Decision Briefs to include context and problem, so that the decision has a clear starting point.
62. As a user, I want Decision Briefs to include source evidence, so that recommendations can be audited.
63. As a user, I want Decision Briefs to include strategic interpretation, so that evidence is connected to business meaning.
64. As a user, I want Decision Briefs to include alternatives considered, so that trade-offs are visible.
65. As a user, I want Decision Briefs to include risks and assumptions, so that the team knows what might be wrong.
66. As a user, I want Decision Briefs to include success metrics, so that the team can measure outcomes later.
67. As a user, I want Decision Briefs to include next steps, so that discussion leads to action.
68. As a user, I want Decision Briefs to include decision status, so that the team knows whether to Go, No-Go, or Validate First.
69. As a developer, I want a deep source ingestion module, so that file upload, metadata capture, and status transitions are testable in isolation.
70. As a developer, I want a deep CSV profiling module, so that visualization metadata can be generated through a stable interface.
71. As a developer, I want a deep PDF knowledge indexing module, so that document extraction, chunking, embedding, and retrieval can be tested independently.
72. As a developer, I want a deep chat orchestration module, so that AI routing, tool usage, source grounding, and response formatting are encapsulated.
73. As a developer, I want shared contracts between frontend and backend, so that UI and API expectations remain consistent.
74. As a developer, I want background processing for files, so that large uploads do not block the user interface.
75. As a developer, I want Langfuse traces for agent runs, so that AI behavior can be inspected during development and demo.

## Implementation Decisions

- Product name for the MVP is Company Intelligence Copilot.
- The app is chat-first. The Chat page is the primary interaction surface.
- The AI role is Company Strategy Consultant, not a generic chatbot.
- The main navigation is limited to Chat, Visualization Data, and Source Data.
- Real authentication is out of scope for MVP. The app supports basic multi-workspaces without user accounts, so the team can create separate workspaces for Developer 1, Developer 2, Developer 3, and Demo.
- Workspace management is intentionally lightweight: users can create and switch the client-selected active workspace from the app header/dashboard area, but Workspace is not a dedicated sidebar menu.
- The active workspace is client UI state, not a server-global `is_active` flag. Workspace-scoped API requests send an explicit `workspace_id`.
- Supported file types for MVP are CSV and PDF.
- Excel is not directly supported in MVP; users can export spreadsheets to CSV before upload.
- Source data is labeled by team, category, and period.
- Team labels are Marketing, Product, Data Analysis, and Business.
- Category labels are Analytics / Metrics, Market Research, Product / Feature, Customer Insight, Business Model, Competitor Analysis, and Revenue / Sales.
- Category labels support multi-select.
- Visualization filters are Team Label, Category Label, and Period.
- File processing uses four statuses: Uploaded, Processing, Ready, and Failed. Processing runs synchronously by default for the demo and can later use background jobs.
- Structured CSV data is parsed and profiled for auto-generated visualizations.
- CSV visualization should produce a generic visual story instead of only raw tables.
- CSV visualization includes executive summary cards, trend explorer, segment breakdown, relationship view, anomaly highlights, and auto insight cards when the underlying data supports them.
- Unstructured PDF data is not forced into charts.
- PDF visualization is represented as a Document Insight view.
- Document Insight uses `source_summary` for the document summary and `source_insight` for key findings, assumptions, risks, opportunities, and source quotes.
- PDF OCR uses Mistral OCR with model `mistral-ocr-latest`, inline base64 document input, `table_format="html"`, and image base64 disabled.
- PDF structuring uses LiteLLM with `RAG_OPENAI_API_BASE_URL`, `RAG_OPENAI_API_KEY`, and `RAG_OPENAI_MODEL`, defaulting to `google/gemini-3.1-flash-lite-preview`.
- PDF processing writes extracted markdown to `storage/extracted/{workspace_id}/{source_id}/ocr.md` and chunk metadata to `storage/extracted/{workspace_id}/{source_id}/chunks.json`.
- Source processing runs synchronously by default for the demo. `RAG_ENABLE_BACKGROUND_PROCESSING=false` keeps sync processing; when enabled later, background failures should fall back to sync processing with a warning.
- Chat can use all relevant sources by default.
- Chat users can override scope by mentioning team, category, period, or source constraints in natural language.
- Chat responses are semi-structured by default: Direct Answer, Evidence, Interpretation, Recommendation / Next Step, and Confidence + Gaps.
- Chat answers must be source-grounded. If data is insufficient, the AI must say so and ask for missing information or label assumptions clearly.
- Chat responses should expose View Sources and View Trace actions.
- View Trace links to or references Langfuse trace information.
- Decision Briefs are generated as formatted chat responses, not as a separate MVP page.
- Decision Brief format includes Decision Title, Context / Problem, Source Evidence, Strategic Interpretation, Recommendation, Alternatives Considered, Risks & Assumptions, Success Metrics, Next Steps, and Recommendation Status.
- Recommendation Status values are Go, No-Go, and Validate First. Approval Status values are Draft, Reviewed, Approved, and Rejected; these are independent from Recommendation Status.
- The frontend uses the existing TanStack Start, TanStack Router, React, and TypeScript foundation.
- The backend uses the existing FastAPI foundation.
- Python remains the primary place for RAG, AI Agent work, and data analysis, consistent with the accepted foundation ADR.
- Backend FastAPI/Pydantic/SQLModel schemas are the validation source of truth. Frontend TypeScript types live locally under `apps/web/src/types`, and `/openapi.json` is the contract reference for source data, visualizations, chat messages, source citations, and decision briefs.
- SQLModel and Alembic should be used for relational app data such as sources, metadata labels, periods, processing jobs, chat sessions, chat messages, generated artifacts, and trace references.
- ChromaDB should be used as the vector database for PDF chunks, document insight retrieval, and company knowledge retrieval.
- Redis and Celery should be available for optional background source processing, but demo processing defaults to synchronous execution.
- OpenAI Agent SDK should be used for AI agent orchestration.
- Langfuse should be used for AI agent observability.
- The issue tracker and triage labels are not configured in the current repository context. This PRD is saved as a local document first, per the requested output.

Major modules to build or modify:

- Workspace Management: handles lightweight workspace creation and client-side workspace switching without authentication.
- Source Data Management: handles upload metadata, team labels, category labels, period, source table listing, status display, and source deletion.
- Source Processing Pipeline: handles transition from Uploaded to Processing to Ready or Failed, supports retrying Failed Sources, and can run synchronously or through optional background processing.
- CSV Profiler and Visualization Generator: deep module that accepts structured rows and returns visualization-ready metadata, chart specs, summary stats, anomalies, and insight text.
- PDF Ingestion and Knowledge Indexer: deep module that OCRs PDF files, writes extracted markdown, chunks content, labels chunks, creates embeddings, stores vectors, and returns Document Insight data.
- Company Knowledge Retrieval: deep module that selects relevant structured summaries and document chunks based on user chat intent, labels, categories, and period.
- AI Consultant Orchestrator: deep module that routes user questions to tools, retrieves sources, formats grounded responses, and records observability traces.
- Decision Brief Generator: deep module that turns chat context and source evidence into a formatted decision brief.
- Langfuse Observability Integration: captures prompts, source retrieval, tool calls, model output, latency, errors, and trace IDs.
- API Contract Alignment: keeps backend schemas, frontend local TypeScript types, and `/openapi.json` aligned for source data, processing status, visualizations, chat responses, citations, traces, and decision briefs.
- Frontend Shell and Navigation: implements the three-page layout with Chat, Visualization Data, and Source Data.
- Chat Interface: implements GPT-like conversation, source and trace display, and formatted Decision Brief rendering.
- Visualization Data Interface: implements auto visualization cards for CSV and Document Insight cards for PDF documents.
- Source Data Interface: implements source library table and Add New Data dialog.

## High-Level Schema

This schema is PRD-level and should guide implementation. It is not intended to be a final migration script.

### Domain Model

- Workspace: a lightweight company/developer context. The MVP supports creating basic workspaces and selecting one in the client UI without authentication, primarily for Developer 1, Developer 2, Developer 3, and Demo environments.
- Source: an uploaded CSV or PDF file plus metadata, labels, period, storage path, processing status, and generated artifacts.
- Source Data: the product page/menu where users manage Sources.
- Source Category: join table for multi-select category labels on a source.
- Source Artifact: generated output from source processing, such as CSV profiles, chart specs, insight cards, source summaries, and source insights.
- Chat Session: a GPT-like conversation thread inside the workspace.
- Chat Message: one user, assistant, or system message inside a chat session.
- Agent Tool Call: simplified record of tools used while generating an assistant response.
- Message Source Citation: source evidence used by an assistant response.
- Decision Brief Draft: a generated decision artifact that appears as a formatted assistant response and can be marked draft, reviewed, approved, or rejected.

### Relational Database Schema

#### `workspace`

Stores lightweight workspaces. Workspaces are selectable from the dashboard/header area and are not shown as a dedicated sidebar menu.

- `id`
- `name`
- `description`
- `created_at`
- `updated_at`

MVP seed workspaces should include:

- Developer 1
- Developer 2
- Developer 3
- Demo

Only one workspace is active in a client UI at a time. All Source Data, Visualization Data, Chat Sessions, and Decision Brief Drafts are scoped by the explicit `workspace_id` sent from that client-selected active workspace.

#### `source_data`

Stores uploaded file metadata. Original uploaded files are stored in local storage, not directly in the database.

- `id`
- `workspace_id`
- `title`
- `team_label`: `marketing`, `product`, `data_analysis`, `business`
- `file_type`: `csv`, `pdf`
- `original_filename`
- `storage_path`
- `period_start`
- `period_end`
- `period_label`
- `processing_status`: `uploaded`, `processing`, `ready`, `failed`
- `processing_error`
- `uploaded_at`
- `processed_at`
- `deleted_at`
- `created_at`
- `updated_at`

Recommended local storage path format:

```text
storage/uploads/{workspace_id}/{source_id}/original.{ext}
```

#### `source_category`

Stores category labels for each source. A source can have multiple categories.

- `id`
- `source_id`
- `category`: `analytics_metrics`, `market_research`, `product_feature`, `customer_insight`, `business_model`, `competitor_analysis`, `revenue_sales`
- `created_at`

#### `source_artifact`

Stores generated source-processing outputs used by Visualization Data and Chat.

- `id`
- `source_id`
- `artifact_type`: `csv_profile`, `chart_spec`, `insight_card`, `source_summary`, `source_insight`
- `title`
- `content_json`
- `created_at`
- `updated_at`

`content_json` stays flexible because source data is generic. Examples:

- CSV profile: column names, inferred types, row count, numeric columns, categorical columns, date columns.
- Chart spec: chart type, x-axis, y-axis, series, labels, display title.
- Insight card: anomaly, trend, interpretation, confidence, related columns.
- Source summary: summary, page count, OCR model, structuring model, extracted markdown path, chunk metadata path, and warnings.
- Source insight: key findings, assumptions, risks, opportunities, and source quotes. Each item should include supporting quote and page number when available.

#### `chat_session`

Stores chat threads.

- `id`
- `workspace_id`
- `title`
- `created_at`
- `updated_at`

#### `chat_message`

Stores user, assistant, and system messages.

- `id`
- `session_id`
- `role`: `user`, `assistant`, `system`
- `content`
- `message_type`: `normal`, `decision_brief`, `command_result`
- `trace_id`
- `created_at`

#### `agent_tool_call`

Stores simplified tool-call summaries for UI/debugging. Full details belong in Langfuse.

- `id`
- `message_id`
- `tool_name`
- `status`: `success`, `failed`
- `summary`
- `created_at`

#### `message_source_citation`

Stores source evidence used by assistant messages.

- `id`
- `message_id`
- `source_id`
- `artifact_id`
- `quote`
- `page_number`
- `created_at`

For CSV citations, `artifact_id` can point to a profile, chart spec, or insight card. For PDF citations, `quote` and `page_number` should be used when available.

#### `decision_brief`

Stores generated Decision Brief Drafts. A brief is not created for every chat. It is created only through a slash command or explicit user confirmation.

- `id`
- `workspace_id`
- `chat_session_id`
- `chat_message_id`
- `title`
- `recommendation_status`: `go`, `no_go`, `validate_first`
- `approval_status`: `draft`, `reviewed`, `approved`, `rejected`
- `content_json`
- `created_at`
- `updated_at`

`content_json` should be structured, not plain markdown:

```json
{
  "context_problem": "...",
  "source_evidence": [],
  "strategic_interpretation": "...",
  "recommendation": "...",
  "alternatives_considered": [],
  "risks_assumptions": [],
  "success_metrics": [],
  "next_steps": []
}
```

### Slash Commands

The Chat page supports MVP slash commands:

- `/decision-brief`: generates a Decision Brief Draft from the current chat context.
- `/sources`: shows sources used in the current discussion or latest assistant response.
- `/trace`: shows the latest Langfuse trace reference.
- `/brief-status <draft|reviewed|approved|rejected>`: updates the latest Decision Brief Draft status in the current chat session.

Decision Briefs represent AI-generated decision drafts, not final company decisions. The AI recommendation status and human approval status must remain separate.

### ChromaDB Schema

Use one ChromaDB collection for MVP:

```text
company_knowledge
```

Each PDF chunk is embedded and stored with rich metadata to improve retrieval precision.

Recommended chunk metadata:

- `workspace_id`
- `source_id`
- `source_title`
- `source_type`: `pdf`
- `team_label`
- `category_labels`
- `period_start`
- `period_end`
- `period_label`
- `document_section`: `executive_summary`, `market_context`, `competitor_analysis`, `customer_insight`, `business_model`, `risk`, `pricing`, `roadmap`, `unknown`
- `section_confidence`
- `content_type`: `summary`, `finding`, `assumption`, `risk`, `opportunity`, `quote`, `raw_text`
- `content_type_confidence`
- `language`
- `page_number`
- `chunk_index`
- `created_at`

`document_section` and `content_type` are assigned by AI extraction during PDF processing. If the model is uncertain, it should use `unknown` and `raw_text`.

### API Contracts Overview

The PRD expects high-level API contracts, not final OpenAPI definitions.

#### Source Data

#### Workspaces

- `POST /workspaces`
  - Creates a lightweight workspace with name and optional description.
  - Used for Developer 1, Developer 2, Developer 3, and Demo contexts.
- `GET /workspaces`
  - Lists available workspaces.
- `GET /workspaces/{workspace_id}`
  - Returns one workspace.
- Workspace selection is client UI state. There is no server-global activate endpoint for MVP.

#### Source Data

- `POST /sources`
  - Creates a source record for the explicit `workspace_id`, uploads a CSV/PDF file to local storage, stores team label, category labels, and period, then starts background processing.
  - Returns source metadata and initial processing status.
- `GET /sources`
  - Lists sources.
  - Requires `workspace_id` and supports filters for team label, category label, period, file type, and processing status.
- `GET /sources/{source_id}`
  - Returns one source with categories, processing status, and generated artifacts.
- `DELETE /sources/{source_id}`
  - Soft-deletes the Source so it is hidden from future analysis while past citations and Decision Brief Drafts remain auditable.
- `POST /sources/{source_id}/retry-processing`
  - Requeues processing for a Failed Source and moves it back toward Processing.

#### Visualization Data

- `GET /visualizations`
  - Returns visualization-ready artifacts from ready sources.
  - Requires `workspace_id` and supports filters for team label, category label, and period. Period filters use range overlap.
- `GET /visualizations/{source_id}`
  - Returns artifacts for a single source.

#### Chat

- `POST /chat/sessions`
  - Creates a chat session.
  - Requires `workspace_id`; the session remains scoped to that Workspace.
- `GET /chat/sessions/{session_id}`
  - Returns chat messages, tool call summaries, source citations, and trace references.
- `POST /chat/sessions/{session_id}/messages`
  - Sends a user message and returns an assistant response.
  - The assistant response includes content, sources, tool call summaries, and optional trace ID.
- `POST /chat/sessions/{session_id}/commands`
  - Executes slash commands such as `/decision-brief`, `/sources`, `/trace`, and `/brief-status`.

Chat auto-selects relevant Sources by default. User messages may narrow Source Scope by mentioning team, category, period, or source constraints in natural language; this scope is evaluated per message and is not a persistent chat filter in MVP.

#### Decision Briefs

- `GET /decision-briefs/{brief_id}`
  - Returns a Decision Brief Draft.
- `PATCH /decision-briefs/{brief_id}/status`
  - Updates approval status for a Decision Brief Draft.

## Technical Architecture Diagrams

### Source Ingestion Flow

```mermaid
flowchart TD
  A[User uploads CSV/PDF] --> B[FastAPI Source Endpoint]
  B --> C[Create source_data row]
  B --> D[Save original file to local storage]
  C --> E[Set status: Uploaded]
  D --> F[Run source processing sync by default or optional background]
  F --> G[Set status: Processing]
  G --> H{File type}
  H -->|CSV| I[CSV Profiler]
  I --> J[Generate csv_profile, chart_spec, insight_card]
  J --> K[Save source_artifact rows]
  H -->|PDF| L[Mistral OCR to extracted markdown]
  L --> M[Chunk markdown with Chonkie]
  M --> N[LiteLLM chunk labeling]
  N --> O[Save extracted ocr.md and chunks.json]
  N --> P[Generate source_summary and source_insight]
  O --> S[Task 4 indexes chunks in ChromaDB]
  P --> K
  K --> Q[Set status: Ready]
  G --> R[Set status: Failed on error]
```

### Chat Consultant Flow

```mermaid
flowchart TD
  A[User sends chat message or slash command] --> B[FastAPI Chat Endpoint]
  B --> C[Save user chat_message]
  C --> D[OpenAI Agent SDK Orchestrator]
  D --> E[Select relevant sources]
  E --> F[Query SQL artifacts and metadata]
  E --> G[Retrieve PDF chunks from ChromaDB]
  D --> H[Run analysis tools when needed]
  F --> I[Company Strategy Consultant response]
  G --> I
  H --> I
  I --> J[Create assistant chat_message]
  I --> K[Save agent_tool_call summaries]
  I --> L[Save message_source_citation rows]
  I --> M[Record Langfuse trace]
  M --> N[Attach trace_id to assistant message]
  J --> O[Return response, sources, tool calls, trace]
```

### Decision Brief Draft Flow

```mermaid
flowchart TD
  A[User runs /decision-brief] --> B[Command Endpoint]
  B --> C[Load current chat session context]
  C --> D[Load relevant citations and artifacts]
  D --> E[Decision Brief Generator]
  E --> F[Generate structured content_json]
  F --> G[Save assistant message with message_type decision_brief]
  G --> H[Create decision_brief row]
  H --> I[Default approval_status: draft]
  I --> J[Render formatted brief in chat]
  K[User runs /brief-status approved] --> L[Update latest brief approval_status]
```

### Data Model Relationship

```mermaid
erDiagram
  WORKSPACE ||--o{ SOURCE_DATA : owns
  SOURCE_DATA ||--o{ SOURCE_CATEGORY : has
  SOURCE_DATA ||--o{ SOURCE_ARTIFACT : produces
  WORKSPACE ||--o{ CHAT_SESSION : owns
  CHAT_SESSION ||--o{ CHAT_MESSAGE : contains
  CHAT_MESSAGE ||--o{ AGENT_TOOL_CALL : records
  CHAT_MESSAGE ||--o{ MESSAGE_SOURCE_CITATION : cites
  SOURCE_DATA ||--o{ MESSAGE_SOURCE_CITATION : referenced_by
  SOURCE_ARTIFACT ||--o{ MESSAGE_SOURCE_CITATION : referenced_by
  CHAT_SESSION ||--o{ DECISION_BRIEF : generates
  CHAT_MESSAGE ||--o| DECISION_BRIEF : renders
```

## Testing Decisions

Good tests should verify external behavior, not implementation details. Tests should assert what users and API consumers can observe: successful uploads create source records, processing status transitions correctly, CSV profiling returns expected visualization metadata, PDF indexing makes relevant text retrievable, chat responses include required structure and citations, and Decision Brief generation includes required sections.

Modules to test:

- Source Data Management should be tested with API-level tests for creating sources, listing sources, filtering by labels and period, and status visibility.
- Source Processing Pipeline should be tested with service-level tests for status transitions, failure handling, and retry behavior.
- CSV Profiler and Visualization Generator should be tested as a deep module with sample CSV inputs and expected visualization metadata outputs.
- PDF Ingestion and Knowledge Indexer should be tested as a deep module with small sample PDFs or extracted text fixtures and expected summary/retrieval outputs.
- Company Knowledge Retrieval should be tested with mixed source metadata to ensure relevant sources are selected by question, team, category, and period.
- AI Consultant Orchestrator should be tested with mocked model and tool calls to verify source-grounded response structure, insufficient-data behavior, and trace reference creation.
- Decision Brief Generator should be tested with fixed evidence inputs to verify all required sections are present.
- Frontend Source Data page should be tested for table rendering, upload dialog fields, labels, categories, period selection, and processing status display.
- Frontend Visualization Data page should be tested for rendering CSV visual story sections and Document Insight sections from API responses.
- Frontend Chat page should be tested for message rendering, semi-structured AI responses, View Sources, View Trace, and Decision Brief formatting.

Prior art in the current codebase:

- The API already has a health endpoint smoke test using FastAPI TestClient. New backend API tests should follow that simple external-behavior style.
- The web app already has a test setup with Vitest. New frontend tests should follow the existing web testing setup and focus on rendered behavior.
- The original contracts package placeholder has been retired for the MVP. Backend FastAPI/Pydantic/SQLModel schemas are the validation source of truth, frontend TypeScript types live locally in `apps/web/src/types`, and `/openapi.json` is the API contract reference.

## Out of Scope

- Real authentication, authorization, or role-based teams.
- Production-grade multi-company workspace support with permissions. MVP only supports lightweight workspace create/switch without auth.
- Direct Excel upload. Users can convert Excel files to CSV for MVP.
- Direct integrations with Mixpanel, Amplitude, GA4, BigQuery, warehouse APIs, CRM tools, or support tools.
- Automatic monthly sync from external systems.
- Real-time collaborative editing.
- Dedicated Decision Brief library page.
- Save to Visualization from chat.
- Pinning chat insights into Visualization Data.
- Full artifact board workflow.
- Advanced role-based access control.
- Production-grade billing, subscription, organization settings, or audit logs.
- Advanced BI dashboard builder with manual chart editing.
- Full live web research or competitor crawling.
- Fully automated final decision-making without human review.
- Production deployment hardening beyond what is needed for the final assignment demo.

## Further Notes

- The product should stay generic and not be tied to EdTech, SaaS, e-commerce, or any single industry. Demo data may use a fictional company later, but the product model should support many company segments.
- The UI should avoid looking like a generic analytics dashboard. The strongest framing is a chat-first intelligence workspace where source data becomes company memory and the AI becomes a strategic consultant.
- The Source Data page is the Single Source of Truth for uploaded company context.
- The Visualization Data page is for automatically generated understanding of uploaded CSV and PDF sources.
- The Chat page is for discussion, strategy, recommendation, assumption challenging, source-grounded analysis, and Decision Brief generation.
- The MVP should prioritize a polished end-to-end demo over broad integrations.
- A future demo scenario should be added later with a fictional company, sample CSV files, and sample PDF documents.
- The course requirement for agents with tools, vector database/embeddings, code execution, observability, and optional multi-agent behavior is satisfied by OpenAI Agent SDK tools, ChromaDB PDF retrieval, internal CSV analysis tools, Langfuse traces, and the Company Strategy Consultant orchestration.
