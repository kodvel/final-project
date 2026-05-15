# TODO: Company Intelligence Copilot Implementation Plan

This task breakdown is derived from `docs/prd.md`.

For Source Data processing architecture, use `docs/architecture.md` as the implementation source of truth.

## Current priority for coding agents

The implementation has been realigned with the latest Source, Visualization Data, and Chat streaming architecture. Continue with the remaining product tasks in the recommended order at the end of this file.

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
- [x] Replace Chat mock interaction with backend chat sessions/messages when the API is ready.
- [x] Replace Visualization Data mock content with backend Visualization Snapshot responses when the API is ready.
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
  - user-triggered only via `POST /sources/{source_id}/retry-processing`; no Celery auto-retry/backoff

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
- Source Data frontend polls every 3 seconds while any Source status is `uploaded` or `processing`, stops when all are `ready` or `failed`.

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
- [x] Source upload stores month-level periods only and derives display labels from month range.

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
- Use shared OpenAI structured extraction (`apps/api/app/services/llm_extraction.py`) to turn computed facts into business-readable summary, findings, risks, opportunities, assumptions, and retrieval-friendly prose chunks. LLM input uses sanitized compact profile data with no local file paths and no raw sample cell values.
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

### Tests

- Backend test: `source_summary` generated from sample CSV.
- Backend test: `source_content` generated and indexed from summarized CSV facts.
- Backend test: `source_insight` generated when useful patterns exist.
- Backend test: invalid CSV marks source as Failed.
- Backend test: CSV raw rows are not blindly indexed into ChromaDB.

### Acceptance criteria

- [x] Uploaded CSV is processed from server-side file storage.
- [x] `source_summary` artifact is saved for CSV Sources.
- [x] `source_content` artifact is saved for CSV Sources.
- [x] CSV `source_content` chunks are indexed in ChromaDB.
- [x] `source_insight` artifact is saved when useful insight exists.
- [x] CSV Ready status requires required artifacts and indexing.

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
- Add Task 3 dependencies: `mistralai`, `openai`, and `chonkie`.
- Add Task 3 config fields:
  - `RAG_MISTRAL_API_KEY`
  - `RAG_OPENAI_API_BASE_URL` (default `https://openrouter.ai/api/v1`)
  - `RAG_OPENAI_API_KEY`
  - `RAG_OPENAI_MODEL`, default `google/gemini-2.5-flash-lite`
  - `RAG_EMBEDDING_API_BASE_URL`, default `https://api.openai.com/v1`
  - `RAG_EMBEDDING_API_KEY`
  - `RAG_EMBEDDING_MODEL`, default `text-embedding-3-small`
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
- Use shared OpenAI structured extraction (`apps/api/app/services/llm_extraction.py`) for chunk labeling with `client.chat.completions.parse()` and Pydantic `response_format=ChunkLabelResponse`. Config uses `RAG_OPENAI_API_BASE_URL`, `RAG_OPENAI_API_KEY`, and `RAG_OPENAI_MODEL`, defaulting to `google/gemini-2.5-flash-lite`.
- Chunk labeling metadata uses fixed labels for `document_section` and `content_type`, plus free-text `topics`, `entities`, and `time_periods`.
- `document_section` labels are `executive_summary`, `market_context`, `customer_insight`, `competitor_analysis`, `financials`, `product_feature`, `risks`, `opportunities`, `recommendation`, `methodology`, `appendix`, and `unknown`.
- `content_type` labels are `narrative`, `table`, `metric`, `quote`, `assumption`, `risk`, `opportunity`, `recommendation`, and `raw_text`.
- Structured extraction uses Pydantic validation; no manual JSON repair needed. If extraction fails after retries, fail the PDF processing instead of silently skipping the chunk.
- Save chunk metadata to:

```text
storage/extracted/{workspace_id}/{source_id}/chunks.json
```

- Use shared OpenAI structured extraction for synthesis to create final Source Artifacts from chunk metadata and representative evidence.
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

### Tests

- Backend test: mocked Mistral OCR and structured extraction output create `source_summary`, `source_content`, and `source_insight` artifacts.
- Backend test: short OCR text creates `source_summary` with warning and skips `source_insight`.
- Backend test: extraction failure marks source as Failed.
- Backend test: PDF `source_content` chunks are indexed in ChromaDB with page metadata.

### Acceptance criteria

- [x] Uploaded PDF is processed from server-side file storage.
- [x] `source_summary` artifact is saved.
- [x] `source_content` artifact is saved.
- [x] `source_insight` artifact is saved when enough useful text is extracted.
- [x] PDF `source_content` chunks are indexed in ChromaDB.
- [x] Extracted OCR markdown is saved to `storage/extracted/{workspace_id}/{source_id}/ocr.md`.
- [x] Chunk metadata is saved to `storage/extracted/{workspace_id}/{source_id}/chunks.json`.
- [x] Short OCR text creates a Ready Source with `source_summary` warnings and no `source_insight`.
- [x] PDF Ready status requires required artifacts and indexing.

---

## Task 4: Company knowledge indexing and retrieval

- **Type:** AFK
- **Blocked by:** Task 3
- **Developer(s):** Developer A + Developer C
- **User stories covered:** 22-27, 43-49, 71

### Product flow

User asks Chat a question that needs company context. The AI retrieves relevant `source_content` chunks from ChromaDB, validates them against SQL, and cites the Source Artifact.

### Backend work

- Configure ChromaDB with collection `embedding_function` so it owns embeddings.
- Create/use collection:

```text
company_knowledge
```

- Index every indexable `source_content.chunks` item using `collection.upsert(documents=..., ids=..., metadatas=...)`.
- Retrieval uses `collection.query(query_texts=[query], ...)`.
- No manual app-generated embeddings; no `knowledge/embeddings.py` runtime path.
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

- [x] `source_content` chunks are indexed into ChromaDB.
- [x] Chroma metadata is rich enough for filtered retrieval.
- [x] Retrieval service returns source references.
- [x] Retrieval service returns compact citation-ready EvidenceBundle items.
- [x] Retrieval service quality-gates weak evidence.
- [x] Retrieval can be used by Chat task later.

---

## Task 4A: Period-based Visualization Composer and snapshot cache

- **Type:** AFK
- **Blocked by:** Task 2, Task 3, Task 4
- **Developer(s):** Developer A + Developer B
- **User stories covered:** 32-40, 41-46

### Product flow

User opens **Visualization Data**, chooses a month range, and sees a cached cross-artifact intelligence board composed from all ready Sources that overlap that period.

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
- Build a compact artifact payload from Source metadata, summaries, insights, and bounded content references.
- Use `extract_visualization_snapshot()` for LLM cross-artifact synthesis when `RAG_OPENAI_API_KEY` is configured.
- Validate LLM output: empty output or uncited non-gap claims must fail composition and trigger fallback.
- Keep deterministic fallback for missing LLM config, invalid LLM output, or LLM runtime failure.
- Build sections:
  - coverage overview
  - executive summary
  - cross-source patterns
  - source cards
  - key findings
  - risks and assumptions
  - opportunities
  - gaps
- Store `_composition_mode` and `_fingerprint` in `content_json`.
- Return cached snapshot if valid; regenerate lazily when missing or stale by comparing current Source/Artifact fingerprint with cached `_fingerprint`.
- Treat `visualization_snapshot` as derived cache, not source of truth.

### Frontend work

- Replace mock Visualization Data content with snapshot API response.
- Use month-level period controls only.
- Do not add team, category, or file type filters to Visualization Data.
- Show teams and categories as grouping/context inside the snapshot.
- Render executive summary and cross-source patterns above supporting Source cards.
- Add a Refresh action that calls the refresh endpoint.

### Tests

- Backend test: snapshot includes all ready overlapping Sources for a month range.
- Backend test: snapshot excludes deleted, processing, and failed Sources.
- Backend test: stale snapshot regenerates after Source Artifact update.
- Backend test: refresh endpoint forces regeneration.
- Backend test: LLM snapshot composition rejects uncited claims and falls back deterministically.
- Backend test: `content_json` includes `_composition_mode` and `_fingerprint`.
- Frontend test: Visualization Data renders snapshot sections.

### Acceptance criteria

- [x] Visualization Data is scoped by Workspace and month range only.
- [x] Snapshot is cached by `workspace_id + period_start_month + period_end_month`.
- [x] Snapshot can be regenerated from Source Artifacts.
- [x] Snapshot items include evidence references where they make claims.
- [x] Snapshot supports LLM cross-artifact composition with deterministic fallback.
- [x] Snapshot regenerates on read when Source/Artifact fingerprint changes.
- [x] Snapshot exposes executive summary and cross-source patterns.

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
  - normal Chat events: `metadata`, `text_delta`, `tool_call`, `tool_result`, `error`
  - no normal Chat `session_created`, `user_message_saved`, `assistant_started`, `sources_used`, `web_sources_used`, or `assistant_completed` events
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
  - right Sources Used panel shown only after citations exist
  - pinned input bar
  - user bubble right-aligned
  - assistant response rendered as natural ChatGPT-like text, not a bubble or heavy card
  - compact assistant process state for safe tool activity, such as `Thinking…`, `Searching company Sources…`, and `Searching web…`
- Load existing session messages.
- Send message to backend through DeltaKit streaming.
- Render user and assistant messages.
- Render streaming text deltas.
- Use `[DONE]` as the completion signal, then refetch the Chat Session to render canonical persisted messages, citations, and tool calls.
- Preserve typed draft text when the user stops or a stream errors.
- Provide a Stop button that aborts the stream; the backend records partial assistant content as `interrupted`.
- Render command result message type if available.
- Chat history should be available from a top dropdown, not the app sidebar and not a Chat left panel.
- Chat history initially shows the latest 5 sessions and supports Show More.

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
- [x] Chat Session is lazily created on first message.
- [x] Chat messages include lifecycle status.
- [x] Chat Session can store conversation summary state.
- [x] ContextBuilder preserves session continuity within token budget.
- [x] Chat stream is DeltaKit-compatible.
- [x] Chat history dropdown shows latest 5 and supports Show More.

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
- Current implementation decision: pre-retrieval is gated by an OpenAI structured-output classifier that returns `RetrievalClassification(needs_retrieval, reason)` via `client.chat.completions.parse()` with Pydantic `response_format`. If classification fails, default to retrieval. The agent still has access to the retrieval tool for follow-up/refinement.
- Use OpenAI Agents SDK with `openai-agents[litellm]` for the single Company Strategy Consultant agent. Convert Agents SDK stream events into DeltaKit-compatible `data:` SSE JSON events. Do not use named SSE `event:` fields or native browser `EventSource` for the POST stream.
- Stream tool activity safely: `tool_call` exposes tool name and call ID only; `tool_result` exposes status only; tool errors expose a safe error message. Do not stream private reasoning, prompts, full tool arguments, raw retrieved chunks, Tavily raw results, or secrets.
- Do not stream raw reasoning. The UI may show muted process status based on tool events.
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
  - call_id nullable
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
- Store tool calls after the run finishes when possible; interrupted or failed runs may persist any tool calls already observed.
- Save only citations actually used in the final answer, not every retrieved candidate.
- The model should return used citation IDs; backend must validate that every used citation ID was included in the provided EvidenceBundle before persisting citations.
- Auto-select relevant Sources by default.
- Narrow Source Scope per message when the user mentions team, category, period, or Source constraints in natural language.
- Cite `source_content` chunks and related Source Artifacts. For PDF evidence, include quote and page number where available.
- If evidence is insufficient, respond with explicit gaps instead of unsupported certainty.
- Web citations must be clearly labeled as Web Source and should not be mixed with uploaded Source evidence without labeling.

### Frontend work

- Render AI responses naturally by default; use sections only when the user asks for structured analysis or when content is complex.
- Sources Used shows citations from DB after stream completion and session refetch.
- Sources Used can render both uploaded Source citations and web citations, grouped per Source with expandable citation detail.
- Hide Sources Used until the active Chat Session has citations; keep session switching available through the Chat header when the panel is hidden.
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

- [x] Chat response uses the unified company knowledge retrieval facade.
- [x] Chat auto-selects relevant Sources by default when the classifier determines local retrieval is needed.
- [x] Natural-language Source Scope constraints work per message.
- [x] Response follows natural consultant style by default and structured formatting when requested.
- [x] Response uses full-session-aware context without passing unlimited raw history.
- [x] Response context is budgeted across conversation history, RAG evidence, web evidence, and output reserve.
- [x] Response includes citations.
- [x] Response citations are validated against provided EvidenceBundle IDs.
- [x] Response can include clearly labeled Tavily web citations.
- [x] Response can say data is insufficient.
- [x] Response stores simplified tool call summaries.
- [x] View Sources works from UI.

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

- [x] User can type `/decision-brief`.
- [x] Decision Brief Draft is generated from chat context.
- [x] Decision Brief Draft uses session citations already used in chat.
- [x] Brief is saved in database.
- [x] Brief appears as formatted assistant response.
- [x] Brief status defaults to Draft.
- [x] Re-running `/decision-brief` creates a new point-in-time draft.
- [x] Insufficient context returns a clear message and no draft.
- [x] Brief can be generated with weak evidence only when gaps are explicit and recommendation defaults toward Validate First.

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

- [x] User can update Decision Brief status from the brief card.
- [x] Draft can become Reviewed, Approved, or Rejected.
- [x] Reviewed can become Approved or Rejected.
- [x] Approved and Rejected are locked.
- [x] Invalid transitions are rejected.

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
- Ensure graceful fallback if Langfuse is disabled or unavailable.

### Frontend work

- Show View Trace or trace reference on assistant response when available.
- Hide or disable trace UI when trace is unavailable.

### Tests

- Test assistant message can store trace ID.
- Test chat still works if Langfuse is unavailable.

### Acceptance criteria

- [x] AI consultant runs create Langfuse traces.
- [x] Assistant messages store trace ID.
- [x] User can view trace reference.
- [x] Core app still works without Langfuse.

Notes:
- Decision Brief generation now issues LLM calls through `services/langfuse_openai.create_openai_client` in [decision_briefs.py](../apps/api/app/services/decision_briefs.py), so structured extraction auto-traces under the active chat span.
- Frontend "View trace" link is hidden unless `VITE_LANGFUSE_HOST` is set; deploys without the env var degrade silently.

---

## Recommended Implementation Order

Completed foundation and migration work: Task 0, Task 1, Task 2, Task 3, Task 4 indexing, Task 4A, Task 5, and Task 10 baseline alignment. Task 4A now includes LLM cross-artifact composition, deterministic fallback, and fingerprint-based stale-on-read.

Remaining work:

1. Task 11: Demo seed data and presentation scenario.

Run Task 10 API contract alignment continuously as schemas change.
