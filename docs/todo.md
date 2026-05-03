# TODO: Company Intelligence Copilot Implementation Plan

This task breakdown is derived from `docs/prd.md`.

The project will be implemented by 3 developers. Each task below explains:

- the user-facing flow it supports
- what must be built across backend, frontend, storage, and tests
- what is intentionally out of scope
- which task blocks or enables other tasks

The goal is not to split by layer only. Each task should produce a verifiable vertical slice whenever possible.

## Suggested 3-Developer Workstream Split

### Developer A — Backend / Data Foundation

Focus:

- SQLModel models
- Alembic migrations
- FastAPI endpoints
- local file storage
- source processing services
- tests for backend behavior

Primary tasks:

- Task 1: Workspace + Source Data CRUD vertical slice
- Task 2: CSV processing backend part
- Task 3: PDF processing backend part
- Task 4: ChromaDB indexing and retrieval

### Developer B — Frontend / Product UI

Focus:

- TanStack routes/pages
- Source Data UI
- Visualization Data UI
- Chat UI
- UI states and frontend tests

Primary tasks:

- Task 1: Workspace + Source Data UI part
- Task 2: CSV Visualization UI part
- Task 3: PDF Insight Board UI part
- Task 5: Chat UI

### Developer C — AI / Integration / Demo

Focus:

- OpenAI Agent SDK orchestration
- source-grounded response behavior
- slash commands
- Decision Brief Draft
- Langfuse at the end
- demo scenario

Primary tasks:

- Task 6: AI Consultant responses
- Task 7: Slash command `/sources`
- Task 8: Decision Brief Draft generation
- Task 9: Decision Brief approval status command
- Task 11: Demo seed data
- Task 12: Langfuse observability integration

### Shared / Early Parallel Task

- Task 0: Architecture skeleton and dependency baseline
- Task 10: API contract alignment

Task 0 should be done before feature work so the team has clear foldering, naming, and baseline dependencies. Task 10 should be maintained as API shapes stabilize.

---

## Task 0: Architecture skeleton and dependency baseline

- **Type:** AFK
- **Blocked by:** None
- **Recommended owner:** Any developer, ideally before Task 1
- **User stories covered:** 69-75 indirectly, developer foundation

### Product flow

No direct product flow. This task prepares the codebase so later backend, frontend, AI, RAG, and background-processing work has obvious homes.

### Important architecture decisions

- Retire `packages/contracts` for MVP. Frontend and backend use different languages, so a TypeScript contracts package does not provide real shared validation.
- Backend source of truth for API validation is FastAPI/Pydantic/SQLModel.
- Frontend keeps local TypeScript types under `apps/web/src/types/`.
- RAG/vector retrieval code uses the domain name `knowledge/`, not `rag/`.
- OpenAI Agent SDK orchestration code lives in `agents/`.
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
      csv_profiler.py
      pdf_extractor.py
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
      chunking.py
      embeddings.py
      retrieval.py
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
- Deep processing modules use capability names, such as `csv_profiler.py`, `pdf_extractor.py`, and `source_processing.py`.
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
- OpenAI SDK / OpenAI Agent SDK dependencies
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

- [ ] Backend folder skeleton exists with clear homes for routes, models, schemas, services, jobs, knowledge, agents, and storage.
- [ ] Alembic is initialized under `apps/api/alembic/`.
- [ ] Scalar API docs are available at `/scalar`.
- [ ] Frontend folder skeleton exists as real files are introduced.
- [ ] TanStack Query provider is configured at the root.
- [ ] `packages/contracts` no longer appears as an active required package.
- [ ] Repo scripts still run without referencing retired contracts.

---

## Task 1: Workspace + Source Data CRUD vertical slice

- **Type:** AFK
- **Blocked by:** None
- **Recommended owner:** Developer A + Developer B
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
- switch active workspace

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
  - `PATCH /workspaces/{workspace_id}/activate`
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
- Scope Source Data endpoints to the active workspace or explicit `workspace_id`.
- On upload:
  - resolve active workspace
  - validate file type
  - create `source_data`
  - save file locally
  - create `source_category` rows
  - set `processing_status`
- On delete:
  - delete source metadata
  - delete category rows
  - delete local uploaded folder/file
  - delete related artifacts if they exist

### Frontend work

- Add sidebar navigation:
  - Chat
  - Visualization Data
  - Source Data
- Add workspace selector/form in app header/dashboard area, not as sidebar menu.
- Workspace UI supports:
  - list workspace options
  - create workspace
  - switch active workspace
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
  - period start
  - period end
  - period label
- Add loading, empty, success, and error states.
- Add delete confirmation.

### Tests

- Backend test: create source with CSV.
- Backend test: create source with PDF.
- Backend test: create workspace.
- Backend test: list workspaces.
- Backend test: switch active workspace.
- Backend test: sources are scoped by workspace.
- Backend test: reject unsupported file type.
- Backend test: list sources.
- Backend test: delete source also deletes metadata and local file.
- Frontend test: Source Data table renders sources.
- Frontend test: workspace selector renders and can switch workspace.
- Frontend test: Add New Data dialog has required fields.

### Acceptance criteria

- [ ] User can upload CSV or PDF.
- [ ] User can create a workspace from header/dashboard area.
- [ ] User can switch active workspace.
- [ ] Source Data table only shows sources for active workspace.
- [ ] Uploaded file is saved locally.
- [ ] Source metadata is saved in database.
- [ ] Source appears in Source Data table.
- [ ] User can delete source.
- [ ] Deleted source disappears from table.
- [ ] Deleted source file is removed from local storage.
- [ ] No edit or replace-file UI exists in MVP.

---

## Task 2: CSV processing into Visualization Data

- **Type:** AFK
- **Blocked by:** Task 1
- **Recommended owner:** Developer A + Developer B
- **User stories covered:** 15, 18, 35-40, 70

### Product flow

User uploads a CSV in Source Data. After processing, user opens **Visualization Data** and sees useful auto-generated visualizations from that CSV.

### Backend work

- Create `source_artifact` schema if not already created.
- Add CSV processing service.
- Read CSV from local storage.
- Infer column types:
  - numeric
  - categorical
  - date/time
  - text
- Generate artifacts:
  - `csv_profile`
  - `chart_spec`
  - `insight_card`
- Store artifacts in `source_artifact.content_json`.
- Update source status:
  - Processing while parsing
  - Ready after artifacts are created
  - Failed if parsing fails
- Implement or extend:
  - `GET /visualizations`
  - `GET /visualizations/{source_id}`

### Frontend work

- Build Visualization Data page.
- Add filters:
  - Team Label
  - Category Label
  - Period
- Render CSV visual story:
  - summary cards
  - trend chart if date/time column exists
  - segment breakdown if categorical columns exist
  - relationship/scatter-style chart if multiple numeric columns exist
  - anomaly/insight cards
- Add empty state when no ready CSV/PDF exists.
- Add failed-source state if processing failed.

### Tests

- Backend test: CSV profile generated from sample CSV.
- Backend test: chart specs generated when date/numeric columns exist.
- Backend test: invalid CSV marks source as Failed.
- API test: `GET /visualizations` returns artifacts grouped by source.
- Frontend test: Visualization Data renders CSV cards/charts from API response.

### Acceptance criteria

- [ ] Uploaded CSV is processed from local storage.
- [ ] CSV profile artifact is saved.
- [ ] Chart spec artifact is saved when possible.
- [ ] Insight card artifact is saved when possible.
- [ ] Visualization Data page displays CSV artifacts.
- [ ] Visualization Data filters work for team/category/period.

---

## Task 3: PDF processing into Insight Board

- **Type:** AFK
- **Blocked by:** Task 1
- **Recommended owner:** Developer A + Developer B
- **User stories covered:** 22-27, 41-46, 71

### Product flow

User uploads a PDF in Source Data. After processing, user opens **Visualization Data** and sees a PDF Insight Board instead of a chart.

### Backend work

- Add PDF extraction service.
- Read PDF from local storage.
- Extract text and page references where possible.
- Generate artifacts:
  - `pdf_summary`
  - `pdf_insight_board`
- PDF Insight Board should include:
  - document summary
  - key findings
  - assumptions
  - risks
  - opportunities
  - source quotes
- Store artifacts in `source_artifact.content_json`.
- Update source status:
  - Processing while extracting
  - Ready after artifacts are created
  - Failed if extraction fails

### Frontend work

- Extend Visualization Data page to render PDF Insight Board.
- Show cards/sections for:
  - Summary
  - Key Findings
  - Assumptions
  - Risks
  - Opportunities
  - Source Quotes
- Keep PDF visuals different from CSV visuals.

### Tests

- Backend test: PDF/text fixture becomes insight board artifact.
- Backend test: extraction failure marks source as Failed.
- Frontend test: PDF Insight Board renders from API response.

### Acceptance criteria

- [ ] Uploaded PDF is processed from local storage.
- [ ] PDF summary artifact is saved.
- [ ] PDF Insight Board artifact is saved.
- [ ] Visualization Data page displays PDF Insight Board.
- [ ] PDF is not forced into chart format.

---

## Task 4: ChromaDB indexing and source retrieval

- **Type:** AFK
- **Blocked by:** Task 3
- **Recommended owner:** Developer A + Developer C
- **User stories covered:** 22-27, 43-49, 71

### Product flow

User asks Chat a question that needs context from uploaded PDFs. The AI can retrieve relevant PDF chunks from ChromaDB and cite the source.

### Backend work

- Configure ChromaDB.
- Create/use collection:

```text
company_knowledge
```

- During PDF processing, chunk extracted text.
- Embed chunks.
- Store chunks in ChromaDB with metadata:
  - workspace_id
  - source_id
  - source_title
  - source_type
  - team_label
  - category_labels
  - period_start
  - period_end
  - period_label
  - document_section
  - section_confidence
  - content_type
  - content_type_confidence
  - language
  - page_number
  - chunk_index
  - created_at
- Use AI extraction for:
  - `document_section`
  - `content_type`
- Use fallback values:
  - document_section: `unknown`
  - content_type: `raw_text`
- Build retrieval service that accepts:
  - query
  - optional team label
  - optional category label
  - optional period
  - optional source id
- Retrieval returns chunk text + source metadata for citations.

### Frontend work

- No major UI required in this task.
- Optional debug display can be hidden from main UI.

### Tests

- Test PDF chunks are prepared with expected metadata.
- Test retrieval returns relevant chunks using seeded/mocked ChromaDB.
- Test retrieval filters by metadata.

### Acceptance criteria

- [ ] PDF chunks are indexed into ChromaDB.
- [ ] Chroma metadata is rich enough for filtered retrieval.
- [ ] Retrieval service returns source references.
- [ ] Retrieval can be used by Chat task later.

---

## Task 5: Chat sessions and GPT-like chat UI

- **Type:** AFK
- **Blocked by:** None
- **Recommended owner:** Developer B + Developer A
- **User stories covered:** 2, 47, 48, 51-56, 72

### Product flow

User opens **Chat**, sees a GPT-like interface, sends a message, receives a basic assistant response, and can reopen the chat history.

### Backend work

- Create schema:
  - `chat_session`
  - `chat_message`
- Implement endpoints:
  - `POST /chat/sessions`
  - `GET /chat/sessions/{session_id}`
  - `POST /chat/sessions/{session_id}/messages`
- Store messages with:
  - role: user, assistant, system
  - content
  - message_type
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
- Load existing session messages.
- Send message to backend.
- Render user and assistant messages.
- Render command result message type if available.

### Tests

- Backend test: create chat session.
- Backend test: send message creates user + assistant messages.
- Backend test: get session returns messages.
- Frontend test: Chat page renders messages and sends input.

### Acceptance criteria

- [ ] User can open Chat page.
- [ ] User can send message.
- [ ] Message is persisted.
- [ ] Assistant response is persisted.
- [ ] Chat history reloads correctly.
- [ ] No AI source-grounding required yet.

---

## Task 6: Source-grounded AI Consultant responses

- **Type:** AFK
- **Blocked by:** Task 2, Task 4, Task 5
- **Recommended owner:** Developer C + Developer A
- **User stories covered:** 3-5, 8-11, 16-17, 49, 51-59, 72

### Product flow

User asks a strategic question in Chat. The Company Strategy Consultant searches relevant source data, analyzes the context, and responds with evidence, interpretation, recommendation, confidence, and gaps.

### Backend work

- Integrate OpenAI Agent SDK.
- Add AI Consultant orchestration service.
- Add source selection logic:
  - from source metadata
  - from source artifacts
  - from ChromaDB retrieval
- Create simplified `agent_tool_call` schema:
  - message_id
  - tool_name
  - status
  - summary
  - created_at
- Create `message_source_citation` schema:
  - message_id
  - source_id
  - artifact_id
  - quote
  - page_number
  - created_at
- Implement tools such as:
  - retrieve sources
  - retrieve PDF context
  - read CSV artifacts
  - summarize evidence
- AI response format:
  - Direct Answer
  - Evidence
  - Interpretation
  - Recommendation / Next Step
  - Confidence + Gaps
- Store assistant response, tool summaries, and citations.

### Frontend work

- Render semi-structured AI responses clearly.
- Add View Sources action on assistant messages.
- View Sources shows citations from DB.
- Show tool call summaries in a collapsed/secondary area if useful.

### Tests

- Backend tests should mock model output and tool calls.
- Test AI response stores citations.
- Test insufficient data response labels gaps.
- Test View Sources data shape.
- Frontend test: source-grounded response renders with View Sources.

### Acceptance criteria

- [ ] Chat response uses relevant source artifacts and/or Chroma retrieval.
- [ ] Response follows semi-structured consultant format.
- [ ] Response includes citations.
- [ ] Response can say data is insufficient.
- [ ] Response stores simplified tool call summaries.
- [ ] View Sources works from UI.

---

## Task 7: Slash command `/sources`

- **Type:** AFK
- **Blocked by:** Task 5, Task 6
- **Recommended owner:** Developer C
- **User stories covered:** 49

### Product flow

User types `/sources` in Chat to inspect which sources were used in the latest assistant response or current discussion.

### Backend work

- Add command parsing for `/sources`.
- Implement:
  - `POST /chat/sessions/{session_id}/commands`
- For `/sources`, fetch latest assistant message citations.
- Return command result message.
- If no sources exist, return helpful empty-state message.

### Frontend work

- Detect slash commands or send input normally and let backend classify.
- Render command result response.

### Tests

- Test `/sources` with existing citations.
- Test `/sources` with no citations.
- Test command result appears in chat.

### Acceptance criteria

- [ ] User can type `/sources`.
- [ ] Chat returns relevant sources.
- [ ] Empty state is clear when no sources are available.

---

## Task 8: Decision Brief Draft generation

- **Type:** AFK
- **Blocked by:** Task 6
- **Recommended owner:** Developer C + Developer A
- **User stories covered:** 6, 12-13, 60-68, 72

### Product flow

After strategic discussion, user types `/decision-brief`. The app generates a formatted Decision Brief Draft in chat. It is not a final company decision; it is a draft artifact.

### Backend work

- Create `decision_brief` schema.
- Add `/decision-brief` command.
- Load current chat context.
- Load relevant citations and artifacts.
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
- Set default `approval_status`:
  - draft
- Save assistant message with `message_type = decision_brief`.
- Save decision brief row linked to chat session and chat message.

### Frontend work

- Render Decision Brief Draft as formatted chat response.
- Show recommendation status badge.
- Show approval status badge.

### Tests

- Test `/decision-brief` creates assistant message.
- Test decision brief row is saved.
- Test required sections exist in `content_json`.
- Test UI renders formatted Decision Brief Draft.

### Acceptance criteria

- [ ] User can type `/decision-brief`.
- [ ] Decision Brief Draft is generated from chat context.
- [ ] Brief is saved in database.
- [ ] Brief appears as formatted assistant response.
- [ ] Brief status defaults to Draft.

---

## Task 9: Decision Brief approval status command

- **Type:** AFK
- **Blocked by:** Task 8
- **Recommended owner:** Developer C
- **User stories covered:** 60, 68

### Product flow

User updates the latest Decision Brief Draft status from chat using `/brief-status <status>`.

### Backend work

- Add `/brief-status <draft|reviewed|approved|rejected>` command.
- Find latest Decision Brief Draft in current chat session.
- Update `approval_status`.
- Return command result message.

### Frontend work

- Render command confirmation.
- If latest brief is visible, reflect updated status when reloaded.

### Tests

- Test valid status update.
- Test invalid status returns helpful error.
- Test no brief exists returns helpful message.

### Acceptance criteria

- [ ] User can update latest brief status.
- [ ] Valid statuses work.
- [ ] Invalid status is rejected.
- [ ] No-brief empty state is clear.

---

## Task 10: API contract alignment

- **Type:** AFK
- **Blocked by:** None
- **Recommended owner:** Any developer, ideally early
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

- [ ] Frontend type names match PRD vocabulary.
- [ ] Frontend enum values match backend enum values.
- [ ] FastAPI OpenAPI output reflects the expected API shapes.
- [ ] Frontend and backend use the same concepts consistently without `packages/contracts`.

---

## Task 11: Demo seed data and presentation scenario

- **Type:** HITL
- **Blocked by:** Task 2, Task 3, Task 6, Task 8
- **Recommended owner:** Developer C + team review
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
- **Recommended owner:** Developer C
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
3. Task 2: CSV processing into Visualization Data
4. Task 3: PDF processing into Insight Board
5. Task 4: ChromaDB indexing and source retrieval
6. Task 6: Source-grounded AI Consultant responses
7. Task 7: Slash command `/sources`
8. Task 8: Decision Brief Draft generation
9. Task 9: Decision Brief approval status command
10. Task 10: API contract alignment
11. Task 11: Demo seed data and presentation scenario
12. Task 12: Langfuse observability integration

## Parallelization Notes for 3 Developers

- Task 0 should be done first because it removes package confusion and creates clear homes for backend, frontend, RAG, agents, jobs, and storage.
- Task 1 should start immediately after Task 0 because many tasks depend on source data.
- Task 5 can start in parallel with Task 1 after Task 0 because basic chat does not depend on source processing.
- Task 2 and Task 3 can start after Task 1.
- Task 4 depends on Task 3 because PDF extraction must exist before indexing.
- Task 6 depends on Task 2, Task 4, and Task 5 because AI needs data artifacts, PDF retrieval, and chat UI/API.
- Task 7, Task 8, and Task 9 are best done after Task 6.
- Task 10 should run continuously as API shapes stabilize, not as a blocking package task.
- Task 11 should be prepared near the end but sample data can be drafted earlier.
- Task 12 must be last because Langfuse will be added after the core web app is complete.
