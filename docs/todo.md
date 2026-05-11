# TODO: Company Intelligence Copilot Implementation Plan

This task breakdown is derived from `docs/prd.md`.

For Source Data processing architecture, use `docs/architecture.md` as the implementation source of truth.

The project will be implemented by 3 developers. Each task below explains:

- the user-facing flow it supports
- what must be built across backend, frontend, storage, and tests
- what is intentionally out of scope
- which task blocks or enables other tasks

The goal is not to split by layer only. Each task should produce a verifiable vertical slice whenever possible.

Developer shorthand used in tasks:

- **Developer A:** Backend / data foundation
- **Developer B:** Frontend / product UI
- **Developer C:** AI / integration / demo

## Migration checklist: align current code with latest architecture

Use this temporary checklist before coding against the latest architecture. It highlights current-code gaps after the architecture update. It is not a source of truth.

Source of truth remains:

- Product and domain language: `docs/CONTEXT.md` and `docs/prd.md`
- Source processing and retrieval architecture: `docs/architecture.md`
- API contract: backend schemas and `/openapi.json`
- UI/UX: `docs/designs/*/DESIGN.md`
- Architecture decisions: `docs/adr/*`

Remove this section once implementation matches the latest architecture. The current implementation was built against earlier assumptions: old CSV visualization artifacts, per-artifact Visualization Data responses, non-streaming Chat, dummy assistant responses, source-only citations, and older Source artifact/period models.

### Source Data processing and Visualization files that must be updated

Use `docs/architecture.md` as the source of truth for this section. The target architecture is: upload Source → extract → normalize → save `source_summary`, `source_content`, optional `source_insight` → index `source_content.chunks` in ChromaDB → mark Source Ready → compose cached period-based Visualization Snapshots.

Backend models, enums, and schemas:

- `apps/api/app/models/enums.py`
  - Current implementation still exposes retired artifact values: `csv_profile`, `chart_spec`, and `insight_card`.
  - Add active artifact value `source_content`.
  - New Source processing work should target `source_summary`, `source_content`, and optional `source_insight`; old artifact values should only remain as backward-compatibility shims if migration requires it.
- `apps/api/app/models/source.py`
  - Current implementation stores `period_start` and `period_end` as `datetime` plus `period_label`.
  - Align to month-level period fields (`period_start_month`, `period_end_month`) and derive display labels server-side.
- `apps/api/app/models/visualization_snapshot.py` (new)
  - Add cached snapshot model keyed by `workspace_id + period_start_month + period_end_month`.
  - Store `scope_hash`, `title`, `content_json`, `source_ids_json`, `artifact_ids_json`, `status`, `generation_error`, and `generated_at`.
- `apps/api/app/schemas/visualization.py`
  - Current schema returns flat `VisualizationArtifactRead` items.
  - Replace/add `VisualizationSnapshotRead` for period-based snapshot responses.

Backend services and missing modules:

- `apps/api/app/services/source_processing.py`
  - Current CSV path creates `csv_profile`, `chart_spec`, and `insight_card`; this is the old architecture.
  - Refactor coordinator so Ready requires required SQL artifacts and ChromaDB indexing success.
- `apps/api/app/services/csv_profiler.py`
  - Current implementation is deterministic profiling only.
  - Split into `services/extractors/csv_extractor.py` and `services/normalizers/csv_normalizer.py`.
  - CSV normalizer must create `source_summary`, `source_content` chunks, and optional `source_insight`; do not index raw rows blindly.
- `apps/api/app/services/pdf_extractor.py`
  - Current implementation creates `source_summary` and `source_insight` only.
  - Add `source_content` artifact from labeled chunks with page references, or split extraction/normalization into `services/extractors/pdf_extractor.py` and `services/normalizers/pdf_normalizer.py`.
- `apps/api/app/services/artifacts.py` (new)
  - Centralize Source Artifact upsert/fetch/replace behavior by `artifact_type` so CSV/PDF retry does not duplicate artifacts.
- `apps/api/app/services/periods.py` (new)
  - Centralize month parsing, range validation, label derivation, and overlap checks.
- `apps/api/app/knowledge/indexing.py` (new)
  - Index every `source_content.chunks` item into ChromaDB collection `company_knowledge` with stable vector IDs and metadata.
  - Delete old vectors on retry and exclude/delete vectors for soft-deleted Sources as required by retrieval/snapshot behavior.
- `apps/api/app/knowledge/chroma.py`, `apps/api/app/knowledge/embeddings.py`, and `apps/api/app/knowledge/retrieval.py`
  - These are currently stubs and must be implemented before Chat or Visualization can depend on indexed Source knowledge.
- `apps/api/app/services/visualizations.py`
  - Current implementation lists individual Source Artifacts with team/category/period filters.
  - Replace with Visualization Composer: find ready, non-deleted Sources overlapping the month range; load `source_summary` and `source_insight`; compose coverage, source cards, findings, risks, assumptions, opportunities, and gaps; cache in `visualization_snapshot`.
- `apps/api/app/routes/visualizations.py`
  - Current route accepts team/category/date filters and returns flat artifacts.
  - New route should require `workspace_id`, `period_start_month`, and `period_end_month`.
  - Add `POST /visualizations/refresh` for forced snapshot regeneration.

Frontend files likely impacted:

- `apps/web/src/types/visualization.ts`
  - Current types still include retired `CsvProfileContent`, `ChartSpecContent`, and `InsightCardContent`.
  - Add `source_content` and `VisualizationSnapshot` types; remove retired artifact types from new UI paths.
- `apps/web/src/features/visualization-data/api.ts`
  - Current API client calls flat `GET /visualizations` and derives KPIs/charts from `chart_spec`.
  - Replace with snapshot fetch by Workspace + month range and add `refreshVisualizationSnapshot()`.
- `apps/web/src/features/visualization-data/hooks/index.ts`
  - Replace artifact-derived hooks (`useKpiCards`, `usePrimaryChart`, `useInsightCards`) with snapshot-based hooks.
- `apps/web/src/routes/visualization-data.tsx`
  - Current page renders old CSV KPI/chart/insight cards and per-PDF Document Insight boards.
  - Replace with period-based snapshot sections.
  - Remove team/category/file-type filters from Visualization Data; keep only month range controls.
  - Add Refresh action wired to `POST /visualizations/refresh`.
- `apps/web/src/routes/source-data.tsx` and `apps/web/src/types/source.ts`
  - Align upload form and types to month-level period fields once backend period contract changes.

Tests that must be updated or added for Source/Visualization:

- `apps/api/tests/test_task1_sources.py`
  - Update period expectations to `period_start_month`/`period_end_month` and derived labels.
- `apps/api/tests/test_task2_visualizations.py`
  - Current assertions likely target flat artifacts and old CSV artifact names. Replace with snapshot behavior and normalized artifact expectations.
- `apps/api/tests/test_task3_pdf_pipeline.py`
  - Add assertions that PDF processing saves `source_content` and indexes chunks with page metadata.
- `apps/api/tests/test_task10_contract.py`
  - Update OpenAPI expectations for `source_content`, month-level period fields, and Visualization Snapshot schemas.
- Add/extend tests for CSV `source_summary`, CSV `source_content`, no raw-row Chroma indexing, stable vector IDs, retry vector replacement, soft-delete exclusion, snapshot cache hit/miss, and refresh regeneration.

Non-negotiable Source/Visualization constraints for coding agents:

- SQL remains the source of truth; ChromaDB is a derived index and must be rebuildable.
- A Source is Ready only after required normalized artifacts exist and required `source_content` chunks are indexed.
- `source_content` is the bridge to ChromaDB and Chat evidence.
- Visualization Data is a cached period-based composed view, not a raw per-Source artifact browser.
- Visualization Data MVP has no team/category/file-type filters; those labels appear inside snapshot content as grouping/context.
- Retired artifact names (`csv_profile`, `chart_spec`, `insight_card`, `visualization_spec`) must not be used for new architecture work.

### Chat and Decision Brief files that must be updated

Backend models and enums:

- `apps/api/app/models/enums.py`
  - Add `MessageStatus`: `pending`, `streaming`, `completed`, `failed`, `interrupted`.
  - Add `CitationType`: `uploaded_source`, `web`.
  - Add `CitationStatus`: `available`, `source_deleted`, `source_failed`, `artifact_missing`, `web_unavailable`.
  - Add active artifact value `source_content`; legacy artifact values (`csv_profile`, `chart_spec`, `insight_card`) are retired by architecture docs and should only remain for backward compatibility if needed.
- `apps/api/app/models/chat.py`
  - Extend `ChatSession` with `last_message_at`, `conversation_summary`, `summary_cutoff_message_id`, and `summary_updated_at`.
  - Extend `ChatMessage` with lifecycle fields: `status`, `error_message`, `metadata_json`, `updated_at`, and `completed_at`.
  - Extend `AgentToolCall` with `input_json` and `output_json`.
  - Evolve `MessageSourceCitation` into a polymorphic citation model that supports uploaded Source citations and Tavily web citations. `source_id` must become nullable for web citations.
- `apps/api/app/models/decision_brief.py`
  - Add `sequence_number`, `context_cutoff_message_id`, `objective`, and `status_updated_at`.

Backend schemas and routes:

- `apps/api/app/schemas/chat.py`
  - Add stream request schema for `POST /chat/messages/stream`: `workspace_id`, optional `session_id`, and `message`.
  - Add/extend read schemas for message status, session summary fields, polymorphic citations, and tool-call JSON fields.
  - Deprecate JSON pair response assumptions from `ChatMessagePairRead` once streaming is the primary path.
- `apps/api/app/schemas/decision_brief.py`
  - Add `DecisionBriefStatusUpdate`.
  - Extend `DecisionBriefRead` with point-in-time fields.
- `apps/api/app/routes/chat.py`
  - Add `POST /chat/messages/stream` returning DeltaKit-compatible `text/event-stream`.
  - Add `limit` and `offset` to `GET /chat/sessions` for latest-5 + Show More history.
  - Keep `GET /chat/sessions/{session_id}` Workspace-scoped and include messages, citations, tool calls, and Decision Brief card data as needed.
  - Retire or keep legacy non-streaming endpoints only as compatibility shims; new work should target the stream endpoint.
- `apps/api/app/routes/decision_briefs.py`
  - Implement `GET /decision-briefs/{brief_id}`.
  - Implement `PATCH /decision-briefs/{brief_id}/status` with valid transition checks and Workspace validation.

Backend services and missing modules:

- `apps/api/app/services/chat.py`
  - Replace `_dummy_assistant_response()` and single JSON pair response flow.
  - Support lazy session creation, message lifecycle transitions, `last_message_at`, interrupted partial content, citation persistence, and DeltaKit stream orchestration.
- `apps/api/app/services/context_builder.py` (new)
  - Build budgeted model context from `conversation_summary`, recent raw messages, current user message, uploaded Source EvidenceBundle, optional Tavily evidence, and reserved output tokens.
  - Refresh `conversation_summary` around 70-80% context capacity.
  - Treat summary as context, not evidence.
- `apps/api/app/knowledge/retrieval.py`
  - Implement the company knowledge retrieval facade: SQL eligible Sources, ChromaDB search, SQL validation/hydration, dedupe, rerank, per-Source diversity cap, quality gate, compact EvidenceBundle.
  - Return stable citation IDs and validate model `used_citation_ids` before persistence.
- `apps/api/app/knowledge/chroma.py`
  - Implement `company_knowledge` collection setup, chunk indexing, filtered search, and source vector deletion.
- `apps/api/app/knowledge/embeddings.py`
  - Implement configured embedding calls.
- `apps/api/app/services/tavily.py` (new)
  - Implement bounded Tavily fallback search and map results to web citation fields.
  - Enforce: use Tavily only when local evidence is weak/empty and the question is public/current/web-answerable.
- `apps/api/app/agents/consultant.py`
  - Implement grounded consultant LLM call/streaming using prepared context and EvidenceBundle.
  - Return final content plus `used_citation_ids`, confidence, and gaps.
- `apps/api/app/agents/prompts.py`
  - Add grounding/system prompt, conversation summary prompt, and structured Decision Brief workflow prompts.
- `apps/api/app/agents/tools.py`
  - Keep tool definitions as guarded service calls, not raw DB access.
- `apps/api/app/services/decision_briefs.py`
  - Implement deterministic `/decision-brief` workflow: insufficient-context gate, structured extraction, evidence mapping, draft JSON generation, citation ID validation, `sequence_number`, and status updates.

Source architecture prerequisites that affect Chat:

- `apps/api/app/models/source.py`
  - Current implementation still needs alignment to month-level `period_start_month` and `period_end_month` if not already done. `period_label` should be derived by backend.
- `apps/api/app/schemas/source.py`, source routes/services, and frontend Source upload types must follow the month-level period contract.
- Source processing must produce `source_summary`, `source_content`, and optional `source_insight`; Chat/RAG depends on `source_content` chunks being indexed in ChromaDB.

Frontend files likely impacted:

- `apps/web/src/routes/chat.tsx` and/or `apps/web/src/features/chat/*`
  - Replace dummy/local or non-streaming interaction with DeltaKit stream consumption.
  - Use `POST /chat/messages/stream`.
  - Render `sources_used`, `web_sources_used`, tool call summaries, interrupted/failed states, and Decision Brief cards.
  - Chat history belongs in a top dropdown: latest 5 first, Show More by offset.
- `apps/web/src/features/decision-briefs/*`
  - Add status card actions: Mark Reviewed, Approve, Reject.
  - Call `PATCH /decision-briefs/{brief_id}/status`.
- `apps/web/src/types/chat.ts` and `apps/web/src/types/decision-brief.ts`
  - Align with backend schemas and `/openapi.json`.

### Tests that must be updated or added

- `apps/api/tests/test_task5_chat.py`
  - Current tests target explicit `POST /chat/sessions`, non-streaming `POST /chat/sessions/{session_id}/messages`, and dummy assistant text.
  - Update tests to parse DeltaKit SSE events from `POST /chat/messages/stream`.
  - Add coverage for lazy session creation, existing-session continuation, wrong Workspace rejection, stream interruption, message status transitions, and history pagination.
- `apps/api/tests/test_task10_contract.py`
  - Add new enum expectations for `MessageStatus`, `CitationType`, and `CitationStatus`.
  - Update expected fields for Chat, citation, and Decision Brief read schemas.
- Source tests such as `apps/api/tests/test_task1_sources.py` may need updates for `period_start_month` and `period_end_month`.
- Visualization/source artifact tests may need updates if they still assert retired artifact types.
- Add retrieval tests for SQL validation, dedupe, rerank, diversity cap, quality gate, and compact EvidenceBundle shape.
- Add citation tests for uploaded Source citations, Tavily web citations, deleted Source warning status, and invalid `used_citation_ids` rejection.
- Add Decision Brief tests for insufficient context, repeated drafts with incrementing `sequence_number`, `context_cutoff_message_id`, valid/invalid approval status transitions, and locked approved/rejected states.

### Non-negotiable constraints for coding agents

- Do not use `.env*` or secret files. Use config objects and test overrides.
- No server-global Active Workspace. Every scoped API call uses explicit `workspace_id` and validates ownership.
- Chat Session Workspace never changes after creation.
- DeltaKit stream format is SSE `data:` JSON with a `type` field plus `data: [DONE]`; do not use named SSE `event:` fields.
- SQL is the source of truth. ChromaDB candidates must be SQL-validated before use.
- `conversation_summary` is context, not evidence.
- Internal company claims require uploaded Source citations.
- Tavily web citations support public/current/external context only.
- Save only citations actually used in the final answer.
- Validate all model-returned `used_citation_ids` against the provided EvidenceBundle.
- Each `/decision-brief` creates a new point-in-time draft. Do not overwrite prior drafts.
- Decision Brief status changes are card actions, not `/brief-status` commands.

---

## Task 0: Architecture skeleton and dependency baseline

- **Type:** AFK
- **Blocked by:** None
- **Developer(s):** Any developer, ideally before Task 1
- **User stories covered:** 69-75 indirectly, developer foundation

### Product flow

No direct product flow. This task prepares the codebase so later backend, frontend, AI, RAG, and background-processing work has obvious homes.

### Important architecture decisions

- Retire `packages/contracts` for MVP. Frontend and backend use different languages, so a TypeScript contracts package does not provide real shared validation.
- Backend source of truth for API validation is FastAPI/Pydantic/SQLModel.
- Frontend keeps local TypeScript types under `apps/web/src/types/`.
- RAG/vector retrieval code uses the domain name `knowledge/`, not `rag/`.
- OpenAI-compatible LLM orchestration code lives in `agents/` or thin LLM helper modules when a deterministic workflow is enough.
- Backend uses layer-first foldering because it matches the course style and is common for small-to-medium FastAPI apps.
- Frontend uses feature-first foldering because it is common in React apps and maps well to user flows.

### Backend folder skeleton

Create or prepare this structure:

```text
apps/api/
  alembic.ini
  alembic/
    env.py
    versions/
      .gitkeep
  app/
    main.py
    core/
      __init__.py
      config.py
      exceptions.py
    db/
      __init__.py
      base.py
      session.py
    models/
      __init__.py
      enums.py
      workspace.py
      source.py
      chat.py
      decision_brief.py
    schemas/
      __init__.py
      common.py
      workspace.py
      source.py
      visualization.py
      chat.py
      decision_brief.py
    routes/
      __init__.py
      workspaces.py
      sources.py
      visualizations.py
      chat.py
      decision_briefs.py
    services/
      __init__.py
      workspaces.py
      sources.py
      source_processing.py
      artifacts.py
      periods.py
      visualizations.py
      chat.py
      decision_briefs.py
    jobs/
      __init__.py
      celery_app.py
      source_processing.py
    knowledge/
      __init__.py
      chroma.py
      indexing.py
      retrieval.py
    extractors/
      __init__.py
      csv_extractor.py
      pdf_extractor.py
    normalizers/
      __init__.py
      csv_normalizer.py
      pdf_normalizer.py
    agents/
      __init__.py
      consultant.py
      prompts.py
      tools.py
    storage/
      __init__.py
      local.py
```

Backend naming rules:

- `routes/`, not `api/routes/`, because the app already lives under `apps/api`.
- `models/source.py` contains `SourceData`, `SourceCategory`, and `SourceArtifact`.
- `models/chat.py` contains `ChatSession`, `ChatMessage`, `AgentToolCall`, and `MessageSourceCitation`.
- `models/enums.py` is the backend enum source of truth.
- CRUD/domain orchestration services use plural domain names, such as `sources.py` and `workspaces.py`.
- Deep processing modules separate extraction, normalization, artifact persistence, indexing, and retrieval.
- Celery task files in `jobs/` stay thin. Testable business logic stays in `services/`.

### Backend dependencies

Add baseline dependencies:

- `sqlmodel`
- `alembic`
- `python-multipart`
- `scalar-fastapi`
- `pydantic-settings`

Add later when the related task starts:

- `celery`
- `redis`
- `chromadb`
- OpenAI-compatible SDK dependencies
- Langfuse dependencies

Expose Scalar API docs at:

```text
/scalar
```

Keep default FastAPI docs enabled:

```text
/docs
/redoc
/openapi.json
```

### Frontend folder skeleton

Create or prepare this structure as files become needed:

```text
apps/web/src/
  routes/
    __root.tsx
    index.tsx
    chat.tsx
    source-data.tsx
    visualization-data.tsx
  components/
    ui/
    layout/
  features/
    workspaces/
      api.ts
      hooks/
      components/
    source-data/
      api.ts
      hooks/
      components/
    visualization-data/
      api.ts
      hooks/
      components/
    chat/
      api.ts
      hooks/
      components/
    decision-briefs/
      api.ts
      hooks/
      components/
  lib/
    api-client.ts
    query-client.ts
  types/
    common.ts
    workspace.ts
    source.ts
    visualization.ts
    chat.ts
    decision-brief.ts
```

Frontend naming rules:

- Keep API calls in each feature folder's `api.ts`.
- Keep React Query hooks in each feature folder's `hooks/`.
- Keep shared frontend DTO/type files in `src/types/` by domain.
- Do not create a single large `types/api.ts` file.

### Frontend dependencies

Add baseline dependency:

- `@tanstack/react-query`

Set up:

- `src/lib/query-client.ts`
- `QueryClientProvider` in `routes/__root.tsx`

Do not add charting or UI component libraries yet. Decide those during Visualization Data UI work.

### UI design alignment

The files under `docs/designs/` are the source of truth for UI/UX. Use them for layout, spacing, visual hierarchy, component styling, and interaction shape. They do not define backend data, product contracts, enum values, or business rules. For content and data, use backend responses, local frontend types, `/openapi.json`, and `docs/prd.md`.

Current frontend shell decisions:

- Use the dark full-screen background and one large rounded white content card shown in the design files.
- Remove the old top header from the main app shell.
- Put Workspace switching in the bottom-left nav profile area. The control must support listing, switching, and creating Workspaces.
- Implement a functional collapsible sidebar. Expanded state shows icons and labels; collapsed state shows icons only. Clicking an icon must perform the same action as clicking the expanded item.
- shadcn/ui is set up in the web app. Use shadcn components for reusable primitives when available, including buttons, inputs, selects, dialogs, dropdowns/popovers, tables, badges, and cards. Use `lucide-react` icons through shadcn/lucide. Do not add a charting library yet; use styled, presentational chart placeholders until Visualization Data contracts are ready.
- Load the design fonts in the web app: DM Sans for headings, Inter for body/UI, and JetBrains Mono for code-like labels.
- Treat Chat and Visualization Data as visual-first pages until backend response shapes are ready. Mock content is allowed only as presentational placeholder content.
- Keep Source Data connected to existing backend responses where available. Design-only filters, stats, and pagination can be presentational until the backend supports them.

Current UI implementation status:

- [x] shadcn/ui baseline is configured under `apps/web/src/components/ui`.
- [x] `lucide-react` icons are available.
- [x] Design fonts and UI tokens are loaded in `apps/web/src/app.css`.
- [x] Main shell uses the dark background and one rounded white content card.
- [x] Old top header is removed.
- [x] Sidebar collapse is functional.
- [x] Workspace switch/create is in the bottom-left nav area.
- [x] Chat page is design-faithful with local mock interaction only.
- [x] Source Data page is design-aligned and keeps existing backend hooks.
- [x] Visualization Data page is design-faithful with mock/presentational content only.
- [ ] Replace Chat mock interaction with backend chat sessions/messages when the API is ready.
- [ ] Replace Visualization Data mock content with backend Visualization Snapshot responses when the API is ready.
- [ ] Wire Source Data filter/stats/pagination UI to backend-supported response shapes when available.

### Repository cleanup

- Remove `packages/contracts` from the workspace if it is still present.
- Remove `@final-project/contracts` from scripts that run all projects.
- Update README references that describe `packages/contracts` as active architecture.
- If historical ADRs mention `packages/contracts`, leave them as historical context or add a short note that the package was retired for the MVP.

### Tests

- Backend import smoke test still passes.
- Frontend typecheck/build still passes after TanStack Query provider setup.
- Root `test`, `lint`, or `check` scripts should not reference retired contracts package.

### Acceptance criteria

- [x] Backend folder skeleton exists with clear homes for routes, models, schemas, services, jobs, knowledge, agents, and storage.
- [x] Alembic is initialized under `apps/api/alembic/`.
- [x] Scalar API docs are available at `/scalar`.
- [x] Frontend folder skeleton exists as real files are introduced.
- [x] TanStack Query provider is configured at the root.
- [x] `packages/contracts` no longer appears as an active required package.
- [x] Repo scripts still run without referencing retired contracts.

---

## Task 1: Workspace + Source Data CRUD vertical slice

- **Type:** AFK
- **Blocked by:** None
- **Developer(s):** Developer A + Developer B
- **User stories covered:** 1, 18-21, 28-31, 69, 74

### Product flow

User opens the app, selects or creates a workspace from the dashboard/header area, then opens **Source Data**, clicks **Add New Data**, uploads a CSV/PDF, selects metadata, submits, and sees the uploaded source in a table for the active workspace. User can delete a source if it is no longer needed.

Workspace is not a sidebar menu. It is a lightweight selector/form in the app header/dashboard area so the team can create separate contexts for Developer 1, Developer 2, Developer 3, and Demo.

### Important MVP decision

Source Data only supports:

- Add new source
- Delete source

Source Data does **not** support edit metadata or replace file in MVP.

Workspace supports:

- list workspaces
- add workspace
- switch the client-selected active workspace in the UI

Workspace does **not** support authentication, authorization, member management, or role permissions in MVP.

### Backend work

- Create database schema for:
  - `workspace`
  - `source_data`
  - `source_category`
- Seed or support creating basic workspaces:
  - Developer 1
  - Developer 2
  - Developer 3
  - Demo
- Implement workspace endpoints:
  - `POST /workspaces`
  - `GET /workspaces`
  - `GET /workspaces/{workspace_id}`
- Do not implement a server-global activate endpoint. Workspace selection is client UI state.
- Implement fixed enum values:
  - team labels: Marketing, Product, Data Analysis, Business
  - category labels: Analytics / Metrics, Market Research, Product / Feature, Customer Insight, Business Model, Competitor Analysis, Revenue / Sales
  - file types: CSV, PDF
  - processing statuses: Uploaded, Processing, Ready, Failed
- Implement local file storage.
- Save uploaded files to:

```text
storage/uploads/{workspace_id}/{source_id}/original.{ext}
```

- Implement FastAPI endpoints:
  - `POST /sources`
  - `GET /sources`
  - `GET /sources/{source_id}`
  - `DELETE /sources/{source_id}`
  - `POST /sources/{source_id}/retry-processing`
- Scope Source Data endpoints to the explicit `workspace_id` sent by the client-selected active workspace.
- On upload:
  - resolve explicit `workspace_id`
  - validate file type
  - create `source_data`
  - save file locally
  - create `source_category` rows
  - set `processing_status`
  - enqueue background processing through Celery/Redis
  - if enqueue fails after upload, keep the Source visible with Failed status and a processing error
- On delete:
  - soft-delete the Source
  - hide it from normal Source Data lists and future analysis
  - retain metadata, artifacts, and citations needed for audit history
  - remove local uploaded file only if no past citation or Decision Brief Draft depends on it
- On retry processing:
  - allow Failed Sources to move back toward Processing
  - enqueue background processing again

### Frontend work

- Add sidebar navigation:
  - Chat
  - Visualization Data
  - Source Data
- Add Workspace selector/form in the bottom-left nav profile area, matching the design shell. Do not use the old top header.
- Workspace UI supports:
  - list workspace options
  - create workspace
  - switch client-selected active workspace
- Add functional sidebar collapse:
  - expanded state shows icons and labels
  - collapsed state shows icons only
  - icon clicks still navigate or open the Workspace switcher
- Current implementation: Workspace switch/create is available from the bottom-left nav control; the old top header is removed.
- Build Source Data page.
- Build source table with columns:
  - title
  - file type
  - team label
  - category labels
  - period
  - status
  - uploaded date
  - delete action
- Build Add New Data dialog with:
  - title
  - file input
  - team label select
  - category multi-select
  - period start month
  - period end month
- Add loading, empty, success, and error states.
- Add delete confirmation.
- Current implementation: Source Data is design-aligned and still uses existing backend hooks for list/upload/delete/retry. Filter controls, stats fallback values, and pagination are presentational until backend response shapes support them.

### Tests

- Backend test: create source with CSV.
- Backend test: create source with PDF.
- Backend test: create workspace.
- Backend test: list workspaces.
- Frontend test: switch client-selected active workspace.
- Backend test: sources are scoped by workspace.
- Backend test: reject unsupported file type.
- Backend test: list sources.
- Backend test: delete source soft-deletes and hides it from normal lists.
- Backend test: cited source remains auditable after delete.
- Backend test: retry processing moves Failed Source back toward Processing.
- Frontend test: Source Data table renders sources.
- Frontend test: workspace selector renders and can switch workspace.
- Frontend test: Add New Data dialog has required fields.

### Acceptance criteria

- [x] User can upload CSV or PDF.
- [x] User can create a Workspace from the bottom-left nav Workspace switcher.
- [x] User can switch active workspace.
- [x] Sidebar can collapse to icon-only mode and still navigate/open Workspace switcher.
- [x] Source Data table only shows sources for active workspace.
- [x] Uploaded file is saved locally.
- [x] Source metadata is saved in database.
- [x] Source appears in Source Data table.
- [x] User can delete source.
- [x] Deleted source disappears from table.
- [x] Deleted source is excluded from future analysis.
- [x] Past citations and Decision Brief Drafts remain explainable after source deletion.
- [ ] Deleted source file is removed from server-side file storage only when no citation or Decision Brief Draft needs it for audit.
- [x] User can retry processing for a Failed Source.
- [x] No edit or replace-file UI exists in MVP.
- [ ] Source upload stores month-level periods only and derives display labels from month range.

---

## Task 2: CSV extraction into normalized Source Artifacts

- **Type:** AFK
- **Blocked by:** Task 1
- **Developer(s):** Developer A + Developer B
- **User stories covered:** 15, 18, 35-40, 70

### Product flow

User uploads a CSV in Source Data. Processing computes reliable facts from the CSV, uses an LLM only for interpretation, and stores normalized Source Artifacts that can power Chat, citations, and Visualization Data.

### Backend work

- Create `source_artifact` schema if not already created.
- Add CSV extractor and normalizer services.
- Read CSV from server-side file storage.
- Deterministically infer column types and analytical roles:
  - metric
  - time dimension
  - segment dimension
  - identifier
  - text
- Compute row count, column count, missing values, numeric stats, date ranges, top categories, data quality warnings, and obvious patterns.
- Use an LLM second pass to turn computed facts into business-readable summary, findings, risks, opportunities, assumptions, and retrieval-friendly prose chunks.
- Generate artifacts:
  - `source_summary` as the required minimum artifact
  - `source_content` as required searchable chunks
  - `source_insight` when useful insight can be generated
- Store artifacts in `source_artifact.content_json`.
- Index `source_content.chunks` in ChromaDB as summarized factual chunks, not raw rows.
- Update source status:
  - Processing while parsing
  - Ready after `source_summary`, `source_content`, and Chroma indexing succeed
  - Failed if required extraction, normalization, or indexing fails

### Frontend work

- Build Visualization Data page.
- Match the Visualization Data design shell and white-card layout.
- Render design-faithful mock content only as a placeholder until backend visualization responses are ready.
- Render period-based Visualization Snapshot responses once Task 5 is available.
- Add empty state when no ready CSV/PDF exists.
- Add failed-source state if processing failed.
- Current implementation note: older CSV-specific artifact names are superseded by `source_summary`, `source_content`, and `source_insight`.

### Tests

- Backend test: `source_summary` generated from sample CSV.
- Backend test: `source_content` generated and indexed from summarized CSV facts.
- Backend test: `source_insight` generated when useful patterns exist.
- Backend test: invalid CSV marks source as Failed.
- Backend test: CSV raw rows are not blindly indexed into ChromaDB.

### Acceptance criteria

- [x] Uploaded CSV is processed from server-side file storage.
- [ ] `source_summary` artifact is saved for CSV Sources.
- [ ] `source_content` artifact is saved for CSV Sources.
- [ ] CSV `source_content` chunks are indexed in ChromaDB.
- [ ] `source_insight` artifact is saved when useful insight exists.
- [ ] CSV Ready status requires required artifacts and indexing.

---

## Task 3: PDF extraction into normalized Source Artifacts

- **Type:** AFK
- **Blocked by:** Task 1
- **Developer(s):** Developer A + Developer B
- **User stories covered:** 22-27, 41-46, 71

### Product flow

User uploads a PDF in Source Data. Processing OCRs the document, preserves page references, labels chunks, and stores normalized Source Artifacts that can power Chat, citations, and Visualization Data.

### Backend work

- Add PDF OCR and Document Insight services.
- Add Task 3 dependencies: `mistralai`, `litellm`, and `chonkie`.
- Add Task 3 config fields:
  - `RAG_MISTRAL_API_KEY`
  - `RAG_OPENAI_API_BASE_URL`
  - `RAG_OPENAI_API_KEY`
  - `RAG_OPENAI_MODEL`, default `google/gemini-3.1-flash-lite-preview`
  - `RAG_MAX_FILE_SIZE_MB`, default `30`
  - `RAG_ENABLE_BACKGROUND_PROCESSING`, default `false`
- Read PDF from server-side file storage.
- Enforce a 30 MB maximum PDF size before inline base64 OCR.
- Use Mistral OCR with model `mistral-ocr-latest`, inline base64 `document_url`, `table_format="html"`, and `include_image_base64=false`.
- If `RAG_MISTRAL_API_KEY` is missing or OCR fails, mark the Source as Failed with a clear processing error.
- Save extracted markdown to:

```text
storage/extracted/{workspace_id}/{source_id}/ocr.md
```

- Add page markers to extracted markdown so later chunks can keep page references.
- Chunk extracted markdown with Chonkie `RecursiveChunker` using `chunk_size=3000` and `min_characters_per_chunk=300`.
- Use LiteLLM for chunk labeling with `RAG_OPENAI_API_BASE_URL`, `RAG_OPENAI_API_KEY`, and `RAG_OPENAI_MODEL`, defaulting to `google/gemini-3.1-flash-lite-preview`.
- Chunk labeling metadata uses fixed labels for `document_section` and `content_type`, plus free-text `topics`, `entities`, and `time_periods`.
- `document_section` labels are `executive_summary`, `market_context`, `customer_insight`, `competitor_analysis`, `financials`, `product_feature`, `risks`, `opportunities`, `recommendation`, `methodology`, `appendix`, and `unknown`.
- `content_type` labels are `narrative`, `table`, `metric`, `quote`, `assumption`, `risk`, `opportunity`, `recommendation`, and `raw_text`.
- LiteLLM JSON outputs must be parsed, repaired once if invalid, and then treated as Failed if still invalid.
- If a chunk labeling call fails after one retry, fail the PDF processing instead of silently skipping the chunk.
- Save chunk metadata to:

```text
storage/extracted/{workspace_id}/{source_id}/chunks.json
```

- Use a LiteLLM synthesis call to create final Source Artifacts from chunk metadata and representative evidence.
- Generate artifacts:
  - `source_summary` as the required minimum artifact
  - `source_content` as required citation-ready chunks
  - `source_insight` when enough text is extracted for useful structured sections
- `source_summary.content_json` should include:
  - summary
  - page count
  - OCR model
  - structuring model
  - extracted markdown path
  - chunk metadata path
  - warnings
- `source_insight.content_json` should include:
  - key findings
  - assumptions
  - risks
  - opportunities
  - source quotes
- Insight items should be citation-ready objects with `text`, `page_number`, and `quote` when available.
- Maximum insight counts are 5 key findings, 3 assumptions, 5 risks, 5 opportunities, and 5 source quotes.
- If OCR produces fewer than 500 meaningful characters, save `source_summary`, skip `source_insight`, set status to Ready, and include a warning in `source_summary.content_json.warnings`.
- On retry, overwrite `ocr.md` and `chunks.json`, replace old vectors, and upsert `source_summary`, `source_content`, and `source_insight` by `artifact_type` instead of creating duplicates.
- Store artifacts in `source_artifact.content_json`.
- Index `source_content.chunks` in ChromaDB.
- Update source status:
  - Processing while extracting
  - Ready after `source_summary`, `source_content`, and Chroma indexing succeed; `source_insight` may be intentionally skipped with a warning
  - Failed if extraction fails
- ChromaDB indexing is part of ready-state for indexable Sources.
- Source processing runs synchronously by default for demo reliability. Add `RAG_ENABLE_BACKGROUND_PROCESSING=false` as the default. If background processing is enabled later but unavailable, fall back to sync processing with a warning.

### Frontend work

- Extend Visualization Data page later to render period-based Visualization Snapshots composed from Source Artifacts.
- Select the insight artifact by `artifactType === "source_insight"`; do not assume the first PDF artifact is the insight artifact.
- Render warnings from `source_summary.contentJson.warnings` when present.
- Show cards/sections for:
  - Summary
  - Key Findings
  - Assumptions
  - Risks
  - Opportunities
  - Source Quotes
- Keep PDF visuals different from CSV visuals.
- Current implementation note: per-PDF Document Insight rendering is superseded by period-based Visualization Snapshots.

### Tests

- Backend test: mocked Mistral OCR and LiteLLM output create `source_summary`, `source_content`, and `source_insight` artifacts.
- Backend test: short OCR text creates `source_summary` with warning and skips `source_insight`.
- Backend test: extraction failure marks source as Failed.
- Backend test: PDF `source_content` chunks are indexed in ChromaDB with page metadata.

### Acceptance criteria

- [x] Uploaded PDF is processed from server-side file storage.
- [x] `source_summary` artifact is saved.
- [ ] `source_content` artifact is saved.
- [x] `source_insight` artifact is saved when enough useful text is extracted.
- [ ] PDF `source_content` chunks are indexed in ChromaDB.
- [x] Extracted OCR markdown is saved to `storage/extracted/{workspace_id}/{source_id}/ocr.md`.
- [x] Chunk metadata is saved to `storage/extracted/{workspace_id}/{source_id}/chunks.json`.
- [x] Short OCR text creates a Ready Source with `source_summary` warnings and no `source_insight`.
- [ ] PDF Ready status requires required artifacts and indexing.

---

## Task 4: Company knowledge indexing and retrieval

- **Type:** AFK
- **Blocked by:** Task 3
- **Developer(s):** Developer A + Developer C
- **User stories covered:** 22-27, 43-49, 71

### Product flow

User asks Chat a question that needs company context. The AI retrieves relevant `source_content` chunks from ChromaDB, validates them against SQL, and cites the Source Artifact.

### Backend work

- Configure ChromaDB.
- Create/use collection:

```text
company_knowledge
```

- Index every indexable `source_content.chunks` item.
- Embed chunks.
- Store chunks in ChromaDB with metadata:
  - workspace_id
  - source_id
  - artifact_id
  - chunk_id
  - source_title
  - file_type
  - team_label
  - category_labels
  - period_start_month
  - period_end_month
  - document_section
  - section_confidence
  - content_type
  - content_type_confidence
  - language
  - page_number
  - chunk_index
  - topics
  - entities
  - time_periods
  - created_at
- Reuse Task 3 AI chunk labels for:
  - `document_section`
  - `content_type`
- Use fallback values:
  - document_section: `unknown`
  - content_type: `raw_text`
- Build retrieval service that accepts:
  - query
  - workspace_id
  - optional natural-language Source Scope parsed by Chat
- Retrieval must query eligible SQL Sources first, search ChromaDB within those Source IDs, then validate and hydrate results from SQL.
- Retrieval returns compact citation-ready evidence with Source, artifact, chunk, quote, page references, row references where available, relevance score, and stable citation IDs.
- Retrieval must deduplicate near-identical chunks, rerank candidates, and apply a small per-Source diversity cap before returning the final EvidenceBundle.
- Retrieval must quality-gate results. Weak or misleading evidence should be marked insufficient rather than injected into Chat context.
- Normal Chat should receive roughly 8-12 final evidence chunks by default, not an unlimited set of ChromaDB candidates.

### Frontend work

- No major UI required in this task.
- Optional debug display can be hidden from main UI.

### Tests

- Test `source_content` chunks are prepared with expected metadata.
- Test retrieval returns relevant chunks using seeded/mocked ChromaDB.
- Test retrieval validates workspace, Ready status, and soft-delete state against SQL.
- Test retrieval deduplicates, reranks, diversity-caps, and quality-gates candidates before returning an EvidenceBundle.
- Test low-quality retrieval returns insufficient evidence metadata rather than noisy chunks.

### Acceptance criteria

- [ ] `source_content` chunks are indexed into ChromaDB.
- [ ] Chroma metadata is rich enough for filtered retrieval.
- [ ] Retrieval service returns source references.
- [ ] Retrieval service returns compact citation-ready EvidenceBundle items.
- [ ] Retrieval service quality-gates weak evidence.
- [ ] Retrieval can be used by Chat task later.

---

## Task 4A: Period-based Visualization Composer and snapshot cache

- **Type:** AFK
- **Blocked by:** Task 2, Task 3, Task 4
- **Developer(s):** Developer A + Developer B
- **User stories covered:** 32-40, 41-46

### Product flow

User opens **Visualization Data**, chooses a month range, and sees a cached intelligence view composed from all ready Sources that overlap that period.

### Backend work

- Create `visualization_snapshot` schema:
  - `workspace_id`
  - `period_start_month`
  - `period_end_month`
  - `scope_hash`
  - `title`
  - `content_json`
  - `source_ids_json`
  - `artifact_ids_json`
  - `status`
  - `generation_error`
  - `generated_at`
- Add unique constraint on `workspace_id`, `period_start_month`, and `period_end_month`.
- Implement `GET /visualizations` requiring `workspace_id`, `period_start_month`, and `period_end_month`.
- Implement `POST /visualizations/refresh` for the same scope.
- Compose snapshots from ready, non-deleted, overlapping Sources.
- Load `source_summary` and `source_insight`; use `source_content` only for evidence references when needed.
- Build sections:
  - coverage overview
  - source cards
  - key findings
  - risks and assumptions
  - opportunities
  - gaps
- Return cached snapshot if valid; regenerate lazily when missing or stale.
- Treat `visualization_snapshot` as derived cache, not source of truth.

### Frontend work

- Replace mock Visualization Data content with snapshot API response.
- Use month-level period controls only.
- Do not add team, category, or file type filters to Visualization Data.
- Show teams and categories as grouping/context inside the snapshot.
- Add a Refresh action that calls the refresh endpoint.

### Tests

- Backend test: snapshot includes all ready overlapping Sources for a month range.
- Backend test: snapshot excludes deleted, processing, and failed Sources.
- Backend test: stale snapshot regenerates after Source Artifact update.
- Backend test: refresh endpoint forces regeneration.
- Frontend test: Visualization Data renders snapshot sections.

### Acceptance criteria

- [ ] Visualization Data is scoped by Workspace and month range only.
- [ ] Snapshot is cached by `workspace_id + period_start_month + period_end_month`.
- [ ] Snapshot can be regenerated from Source Artifacts.
- [ ] Visualization Data does not rely on per-Source `visualization_spec` artifacts.
- [ ] Snapshot items include evidence references where they make claims.

---

## Task 5: Chat sessions and GPT-like chat UI

- **Type:** AFK
- **Blocked by:** None
- **Developer(s):** Developer B + Developer A
- **User stories covered:** 2, 47, 48, 51-56, 72

### Product flow

User opens **Chat**, sees a GPT-like interface, sends a message, receives a basic streamed assistant response, and can reopen Chat history from a top dropdown.

### Backend work

- Create schema:
  - `chat_session`
  - `chat_message`
- Add `chat_session.last_message_at` for history ordering.
- Add Chat Session context summary fields:
  - `conversation_summary`
  - `summary_cutoff_message_id`
  - `summary_updated_at`
- Add Chat Message lifecycle fields:
  - `status`: `pending`, `streaming`, `completed`, `failed`, `interrupted`
  - `error_message`
  - `metadata_json`
  - `updated_at`
  - `completed_at`
- Implement endpoints:
  - `GET /chat/sessions?workspace_id=&limit=5&offset=0`
  - `GET /chat/sessions/{session_id}`
  - `POST /chat/messages/stream`
- Lazily create a Chat Session on first message when `session_id` is missing.
- Derive Chat Session title from the first user message.
- Keep Chat Sessions permanently scoped to the Workspace used at creation time.
- Prepare a ContextBuilder service for later AI responses:
  - load all messages in the Chat Session;
  - summarize older messages into `conversation_summary` when messages move out of the recent raw window;
  - keep recent raw messages and the current user message raw;
  - treat conversation summary as context, not evidence.
- Stream responses through DeltaKit-compatible SSE:
  - `text/event-stream`
  - `data:` JSON objects with a `type` field
  - `data: [DONE]` sentinel
- Store messages with:
  - role: user, assistant, system
  - content
  - message_type
  - status
  - created_at
- For this task, assistant response can be simple/dummy.
- Real AI Consultant comes in Task 6.

### Frontend work

- Build Chat page.
- Create GPT-like layout:
  - message list
  - input box
  - send button
  - loading state
- Match the Chat design shell:
  - left chat area
  - right Sources Used panel
  - pinned input bar
  - assistant response card with evidence, interpretation, recommended action, View Sources, View Trace, and Generate Decision Brief actions
- Local mock chat interaction is allowed before backend chat persistence is ready. Replace mock content with backend messages and citations once API responses are available.
- Load existing session messages.
- Send message to backend through DeltaKit streaming.
- Render user and assistant messages.
- Render streaming text deltas.
- Render command result message type if available.
- Chat history should be available from a top dropdown, not the app sidebar and not a Chat left panel.
- Chat history initially shows the latest 5 sessions and supports Show More.
- Current implementation: Chat is design-faithful and wired to backend Chat Sessions/messages with a Task 5 dummy assistant response. Real source-grounded AI responses, citations, Tavily fallback, slash commands, Decision Brief generation, and traces are still later tasks.

### Tests

- Backend test: create chat session.
- Backend test: first streamed message lazily creates session.
- Backend test: existing session continues when `session_id` is supplied.
- Backend test: stream creates user + assistant messages.
- Backend test: interrupted stream leaves assistant message status `interrupted`.
- Backend test: get session returns messages.
- Backend test: session history returns latest 5 and supports offset Show More.
- Backend test: ContextBuilder includes all short-session messages raw.
- Backend test: ContextBuilder uses conversation summary plus recent raw messages for long sessions.
- Frontend test: Chat page renders messages and sends input.
- Frontend test: DeltaKit stream updates assistant message text.

### Acceptance criteria

- [x] User can open Chat page.
- [x] User can send message.
- [x] User can open the design-aligned Chat page with local mock messages.
- [x] User can submit a local mock message and receive a mock assistant response.
- [x] Message is persisted.
- [x] Assistant response is persisted.
- [x] Chat history reloads correctly.
- [x] No AI source-grounding required yet.
- [ ] Chat Session is lazily created on first message.
- [ ] Chat messages include lifecycle status.
- [ ] Chat Session can store conversation summary state.
- [ ] ContextBuilder preserves session continuity within token budget.
- [ ] Chat stream is DeltaKit-compatible.
- [ ] Chat history dropdown shows latest 5 and supports Show More.

---

## Task 6: Source-grounded AI Consultant responses

- **Type:** AFK
- **Blocked by:** Task 2, Task 4, Task 5
- **Developer(s):** Developer C + Developer A
- **User stories covered:** 3-5, 8-11, 16-17, 49, 51-59, 72

### Product flow

User asks a strategic question in Chat. The Company Strategy Consultant retrieves relevant uploaded Source evidence first, optionally uses Tavily only when local evidence is weak and the question is web-capable, and streams a grounded response with evidence, interpretation, confidence, and gaps.

### Backend work

- Add AI Consultant orchestration service.
- Use the configured OpenAI-compatible client/model for LLM calls. Do not make Decision Brief generation an autonomous agent workflow in this task.
- Keep retrieval deterministic and service-owned. The model must not query raw DB directly.
- Build normal Chat model context through ContextBuilder:
  - older messages summarized into `conversation_summary`;
  - recent messages included raw;
  - current user message included raw;
  - uploaded Source EvidenceBundle included separately;
  - Tavily web evidence included only when fallback is allowed and used.
- ContextBuilder must own total prompt budget across conversation history, uploaded Source RAG evidence, optional Tavily web evidence, and reserved output tokens.
- Always reserve output tokens before prompt assembly. Do not fill the entire context window with history or RAG chunks.
- When budget is tight, drop lower-ranked RAG chunks and older redundant raw messages before dropping grounding rules, current user message, or high-quality uploaded Source evidence.
- Keep RAG evidence compact and avoid burying strongest evidence in the middle of a long prompt.
- The model must be instructed that `conversation_summary` is context, not evidence. Internal company factual claims still require uploaded Source citations.
- Add source selection logic:
  - from source metadata
  - from source artifacts
  - from ChromaDB retrieval
- Extend simplified `agent_tool_call` schema:
  - message_id
  - tool_name
  - status
  - summary
  - input_json
  - output_json
  - created_at
- Extend `message_source_citation` into a polymorphic citation schema:
  - message_id
  - citation_type: `uploaded_source`, `web`
  - ordinal
  - source_id nullable
  - artifact_id nullable
  - chunk_id nullable
  - url nullable
  - title nullable
  - domain nullable
  - provider nullable
  - provider_request_id nullable
  - published_date nullable
  - favicon_url nullable
  - quote
  - snippet
  - page_number
  - row_refs_json
  - relevance_score
  - citation_status
  - retrieved_at
  - created_at
- Implement tools such as:
  - retrieve company knowledge
  - validate source evidence
  - summarize evidence
  - Tavily web search fallback
- Tavily web search is allowed only when uploaded Source evidence is weak or empty and the question is public/current/web-answerable.
- Recommended Tavily defaults:
  - `max_results=5`
  - `search_depth=basic`
  - `include_answer=false`
  - `include_raw_content=false`
  - `include_images=false`
- AI response format:
  - Direct Answer
  - Evidence
  - Interpretation
  - Recommendation / Next Step
  - Confidence + Gaps
- Store assistant response, tool summaries, and citations.
- Save only citations actually used in the final answer, not every retrieved candidate.
- The model should return used citation IDs; backend must validate that every used citation ID was included in the provided EvidenceBundle before persisting citations.
- Auto-select relevant Sources by default.
- Narrow Source Scope per message when the user mentions team, category, period, or Source constraints in natural language.
- Cite `source_content` chunks and related Source Artifacts. For PDF evidence, include quote and page number where available.
- If evidence is insufficient, respond with explicit gaps instead of unsupported certainty.
- Web citations must be clearly labeled as Web Source and should not be mixed with uploaded Source evidence without labeling.

### Frontend work

- Render semi-structured AI responses clearly.
- Add View Sources action on assistant messages.
- View Sources shows citations from DB.
- Sources Used can render both uploaded Source citations and web citations.
- Old citations that point to deleted/failed/reprocessed Sources render with a warning/disabled state.
- Show tool call summaries in a collapsed/secondary area if useful.

### Tests

- Backend tests should mock model output and tool calls.
- Test AI response stores citations.
- Test AI response receives conversation summary plus recent raw messages when session is long.
- Test ContextBuilder reserves output budget and trims lower-priority context first.
- Test ContextBuilder does not let RAG chunks crowd out the current user message or grounding rules.
- Test summary-only facts are not saved as Source citations.
- Test invalid model citation IDs are rejected or repaired before persistence.
- Test Tavily fallback stores web citations when local evidence is weak and query is web-capable.
- Test source-specific/internal questions do not use Tavily when local evidence is missing.
- Test insufficient data response labels gaps.
- Test View Sources data shape.
- Test deleted Source citations remain visible with warning status when loading old messages.
- Frontend test: source-grounded response renders with View Sources.

### Acceptance criteria

- [ ] Chat response uses the unified company knowledge retrieval facade.
- [ ] Chat auto-selects relevant Sources by default.
- [ ] Natural-language Source Scope constraints work per message.
- [ ] Response follows semi-structured consultant format.
- [ ] Response uses full-session-aware context without passing unlimited raw history.
- [ ] Response context is budgeted across conversation history, RAG evidence, web evidence, and output reserve.
- [ ] Response includes citations.
- [ ] Response citations are validated against provided EvidenceBundle IDs.
- [ ] Response can include clearly labeled Tavily web citations.
- [ ] Response can say data is insufficient.
- [ ] Response stores simplified tool call summaries.
- [ ] View Sources works from UI.

---

## Task 8: Decision Brief Draft generation

- **Type:** AFK
- **Blocked by:** Task 6
- **Developer(s):** Developer C + Developer A
- **User stories covered:** 6, 12-13, 60-68, 72

### Product flow

After strategic discussion, user types `/decision-brief`. The app generates a formatted Decision Brief Draft in chat from the current Chat Session conversation and citations already used in that session. It is not a final company decision; it is a point-in-time draft artifact.

### Backend work

- Create `decision_brief` schema.
- Add `/decision-brief` command.
- Add point-in-time fields:
  - `sequence_number`
  - `context_cutoff_message_id`
  - `objective`
  - `status_updated_at`
- Load all messages in the current Chat Session.
- Load all citations already used in the current Chat Session.
- Reuse `conversation_summary` for efficiency where helpful, but keep the workflow full-session-aware.
- For long sessions, process messages in chunks and merge structured extraction results rather than silently dropping older decision context.
- Do not run broad Source retrieval again for `/decision-brief` in the MVP.
- If the session has insufficient context or cited evidence, return a clear command result instead of generating a weak draft:

```text
Belum ada context yang cukup untuk membuat Decision Brief Draft.
Diskusikan keputusan, opsi, risiko, dan evidence terlebih dahulu, lalu jalankan /decision-brief lagi.
```

- Generate the draft through deterministic workflow steps with structured LLM calls:
  1. extract decision context from conversation;
  2. map cited evidence to options, risks, assumptions, and gaps;
  3. draft structured Decision Brief JSON;
  4. validate citation IDs in code before saving.
- Generate structured `content_json` with:
  - context_problem
  - source_evidence
  - strategic_interpretation
  - recommendation
  - alternatives_considered
  - risks_assumptions
  - success_metrics
  - next_steps
- Set `recommendation_status`:
  - go
  - no_go
  - validate_first
- If generated with weak or missing citations, prefer `validate_first` and list evidence gaps.
- Set default `approval_status`:
  - draft
- Save assistant message with `message_type = decision_brief`.
- Save decision brief row linked to chat session and chat message.
- Each `/decision-brief` creates a new Decision Brief row. Do not overwrite previous drafts.
- Set `context_cutoff_message_id` to the latest message included in the brief context.

### Frontend work

- Render Decision Brief Draft as formatted chat response.
- Show recommendation status badge.
- Show approval status badge.
- Show Decision Brief as a card with status actions provided by Task 9.

### Tests

- Test `/decision-brief` creates assistant message.
- Test decision brief row is saved.
- Test insufficient context returns the standard command result and does not create a brief.
- Test repeated `/decision-brief` in one Chat Session creates sequence #1, #2, etc.
- Test long-session Decision Brief extraction uses older context through summary/chunked extraction.
- Test draft uses citations already present in the Chat Session instead of broad Source retrieval.
- Test required sections exist in `content_json`.
- Test UI renders formatted Decision Brief Draft.

### Acceptance criteria

- [ ] User can type `/decision-brief`.
- [ ] Decision Brief Draft is generated from chat context.
- [ ] Decision Brief Draft uses session citations already used in chat.
- [ ] Brief is saved in database.
- [ ] Brief appears as formatted assistant response.
- [ ] Brief status defaults to Draft.
- [ ] Re-running `/decision-brief` creates a new point-in-time draft.
- [ ] Insufficient context returns a clear message and no draft.
- [ ] Brief can be generated with weak evidence only when gaps are explicit and recommendation defaults toward Validate First.

---

## Task 9: Decision Brief approval status actions

- **Type:** AFK
- **Blocked by:** Task 8
- **Developer(s):** Developer C
- **User stories covered:** 60, 68

### Product flow

User updates a Decision Brief Draft status from the Decision Brief card in Chat using explicit actions such as Mark Reviewed, Approve, and Reject.

### Backend work

- Implement `PATCH /decision-briefs/{brief_id}/status`.
- Validate that the Decision Brief belongs to the requested Workspace context.
- Update `approval_status` only through valid transitions:

```text
draft -> reviewed
draft -> approved
draft -> rejected
reviewed -> approved
reviewed -> rejected
approved = locked
rejected = locked
```

- Reject invalid transitions with a helpful error.
- Update `status_updated_at`.

### Frontend work

- Render status actions on the Decision Brief card:
  - Draft: Mark Reviewed, Approve, Reject
  - Reviewed: Approve, Reject
  - Approved: read-only locked
  - Rejected: read-only locked
- On action click, call `PATCH /decision-briefs/{brief_id}/status` and update the card status.

### Tests

- Test valid status transitions.
- Test invalid status transitions return helpful error.
- Test approved and rejected briefs are locked.
- Test status update validates Workspace scope.

### Acceptance criteria

- [ ] User can update Decision Brief status from the brief card.
- [ ] Draft can become Reviewed, Approved, or Rejected.
- [ ] Reviewed can become Approved or Rejected.
- [ ] Approved and Rejected are locked.
- [ ] Invalid transitions are rejected.

---

## Task 10: API contract alignment

- **Type:** AFK
- **Blocked by:** None
- **Developer(s):** Any developer, ideally early
- **User stories covered:** 73

### Product flow

No direct product flow. This task keeps frontend and backend aligned while other tasks are built, without using a shared TypeScript contracts package.

### Work to do

- Treat backend FastAPI/Pydantic/SQLModel schemas as the validation source of truth.
- Keep frontend TypeScript types local under `apps/web/src/types/`.
- Define or update frontend type files for:
  - source metadata
  - processing status
  - team labels
  - category labels
  - source artifacts
  - chat session
  - chat message
  - tool call summary
  - citation
  - decision brief draft
- Keep names consistent with PRD schema.
- Keep enum values consistent with backend enum values in `models/enums.py`.
- Use FastAPI's generated `/openapi.json` as the API contract reference.
- If time allows later, optionally generate frontend types from OpenAPI. This is not required for MVP.

### Tests

- Backend schema tests or API tests verify request/response shapes where useful.
- Frontend typecheck verifies local types compile.
- Frontend API client code uses the local type files consistently.

### Acceptance criteria

- [x] Frontend type names match PRD vocabulary.
- [x] Frontend enum values match backend enum values.
- [x] FastAPI OpenAPI output reflects the expected API shapes.
- [x] Frontend and backend use the same concepts consistently without `packages/contracts`.

---

## Task 11: Demo seed data and presentation scenario

- **Type:** HITL
- **Blocked by:** Task 2, Task 3, Task 6, Task 8
- **Developer(s):** Developer C + team review
- **User stories covered:** Final assignment demo scenario

### Product flow

The team prepares a reliable final demo that shows the app value end-to-end.

### Work to do

- Choose fictional company/product context.
- Prepare at least one CSV source.
- Prepare at least one PDF source.
- Upload sources through the app.
- Verify Visualization Data looks useful.
- Prepare demo chat prompts.
- Verify AI Consultant can answer using sources.
- Generate one Decision Brief Draft.
- Document demo script.

### Acceptance criteria

- [ ] Demo company is chosen.
- [ ] Demo CSV is ready.
- [ ] Demo PDF is ready.
- [ ] Demo flow covers Source Data → Visualization Data → Chat → Decision Brief Draft.
- [ ] Demo can be repeated reliably.

---

## Task 12: Langfuse observability integration

- **Type:** AFK
- **Blocked by:** Core web app complete, especially Task 6, Task 8, Task 9
- **Developer(s):** Developer C
- **User stories covered:** 50, 75

### Product flow

After the web app works, AI responses and Decision Brief generation become observable through Langfuse. User can view trace references for AI responses.

### Important sequencing decision

Langfuse is implemented last. Core chat and AI Consultant must work without Langfuse first.

### Backend work

- Integrate Langfuse into AI Consultant orchestration.
- Trace:
  - user prompt
  - selected sources
  - tool calls
  - ChromaDB retrieval
  - AI response
  - Decision Brief generation
- Store `trace_id` on assistant chat messages.
- Treat trace references as optional observability, not evidence.
- Add `/trace` command.
- Ensure graceful fallback if Langfuse is disabled or unavailable.

### Frontend work

- Show View Trace or trace reference on assistant response when available.
- Render `/trace` command result.
- Hide or disable trace UI when trace is unavailable.

### Tests

- Test assistant message can store trace ID.
- Test `/trace` returns latest trace when available.
- Test chat still works if Langfuse is unavailable.

### Acceptance criteria

- [ ] AI consultant runs create Langfuse traces.
- [ ] Assistant messages store trace ID.
- [ ] User can view trace reference.
- [ ] `/trace` command works.
- [ ] Core app still works without Langfuse.

---

## Recommended Implementation Order

0. Task 0: Architecture skeleton and dependency baseline
1. Task 1: Workspace + Source Data CRUD vertical slice
2. Task 5: Chat sessions and GPT-like chat UI
3. Task 2: CSV extraction into normalized Source Artifacts
4. Task 3: PDF processing into Insight Board
5. Task 4: ChromaDB indexing and source retrieval
6. Task 6: Source-grounded AI Consultant responses
7. Task 8: Decision Brief Draft generation
8. Task 9: Decision Brief approval status actions
9. Task 10: API contract alignment
10. Task 11: Demo seed data and presentation scenario
11. Task 12: Langfuse observability integration

## Parallelization Notes for 3 Developers

- Task 0 should be done first because it removes package confusion and creates clear homes for backend, frontend, RAG, agents, jobs, and storage.
- Task 1 should start immediately after Task 0 because many tasks depend on source data.
- Task 5 can start in parallel with Task 1 after Task 0 because basic chat does not depend on source processing.
- Task 2 and Task 3 can start after Task 1.
- Task 4 depends on Task 3 because PDF extraction must exist before indexing.
- Task 6 depends on Task 2, Task 4, and Task 5 because AI needs data artifacts, PDF retrieval, and chat UI/API.
- Task 8 and Task 9 are best done after Task 6.
- Task 10 should run continuously as API shapes stabilize, not as a blocking package task.
- Task 11 should be prepared near the end but sample data can be drafted earlier.
- Task 12 must be last because Langfuse will be added after the core web app is complete.
