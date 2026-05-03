# AGENTS.md

## Project overview

This project is **Company Intelligence Copilot**: a chat-first company intelligence workspace that turns uploaded company Sources into grounded strategic discussion, visual understanding, and Decision Brief Drafts.

The MVP has three main product areas:

- **Chat** — GPT-style strategy workspace with a Company Strategy Consultant that answers with source-grounded evidence, interpretation, recommendations, confidence, and gaps.
- **Visualization Data** — generated Source Artifact views for uploaded CSV and PDF Sources.
- **Source Data** — the source management page for uploading, labeling, tracking, retrying, and soft-deleting Sources.

Core stack:

- Frontend: TanStack Start, TanStack Router, React, TypeScript.
- Backend: FastAPI, Python, SQLModel, Alembic.
- Processing: Redis, Celery.
- Knowledge retrieval: ChromaDB for PDF chunks; SQL Source Artifacts for CSV/PDF generated outputs.
- AI/observability: OpenAI Agent SDK and Langfuse.

## Read first before implementing

Use these docs as the source of truth before changing behavior:

- [`docs/CONTEXT.md`](docs/CONTEXT.md) — domain language, relationships, and resolved ambiguities. Read this first for naming and product semantics.
- [`docs/prd.md`](docs/prd.md) — complete product requirements, MVP scope, user stories, architecture, data model, API contracts, and testing expectations.
- [`docs/todo.md`](docs/todo.md) — implementation order, workstream split, task dependencies, acceptance criteria, and foldering decisions.

## Architecture decisions

Read relevant ADRs before touching related areas:

- [`docs/adr/0001-foundation-template.md`](docs/adr/0001-foundation-template.md) — monorepo foundation, frontend/backend stack, and retired `packages/contracts` note.
- [`docs/adr/0002-client-selected-active-workspace.md`](docs/adr/0002-client-selected-active-workspace.md) — Active Workspace is client-selected UI state; API requests send explicit `workspace_id`.
- [`docs/adr/0003-soft-delete-sources-for-auditability.md`](docs/adr/0003-soft-delete-sources-for-auditability.md) — Source deletion is soft delete so past citations and Decision Brief Drafts stay auditable.
- [`docs/adr/0004-background-source-processing-from-first-upload.md`](docs/adr/0004-background-source-processing-from-first-upload.md) — Source upload should enqueue Redis/Celery processing from the first vertical slice.

## UI design context

Use these docs and assets for visual implementation:

- [`docs/designs/chat/DESIGN.md`](docs/designs/chat/DESIGN.md) — Chat UI/UX source of truth.
- [`docs/designs/chat/code.html`](docs/designs/chat/code.html) — Chat reference HTML.
- [`docs/designs/chat/screen.png`](docs/designs/chat/screen.png) — Chat visual reference.
- [`docs/designs/source/DESIGN.md`](docs/designs/source/DESIGN.md) — Source Data UI/UX source of truth.
- [`docs/designs/source/code.html`](docs/designs/source/code.html) — Source Data reference HTML.
- [`docs/designs/source/screen.png`](docs/designs/source/screen.png) — Source Data visual reference.
- [`docs/designs/visualization/DESIGN.md`](docs/designs/visualization/DESIGN.md) — Visualization Data UI/UX source of truth.
- [`docs/designs/visualization/code.html`](docs/designs/visualization/code.html) — Visualization Data reference HTML.
- [`docs/designs/visualization/screen.png`](docs/designs/visualization/screen.png) — Visualization Data visual reference.

## Domain rules to preserve

- Say **Workspace**, not account, organization, or tenant.
- Say **Active Workspace** only for the client-selected workspace in the current browser/app session.
- Say **Source** for one uploaded file plus metadata, labels, Processing Status, and generated artifacts.
- Say **Source Data** for the product page/menu where users manage Sources.
- Processing Status values are **Uploaded**, **Processing**, **Ready**, and **Failed**.
- A Chat Session belongs to exactly one Workspace and must not follow later Active Workspace switches.
- Chat uses all relevant Sources by default and narrows **Source Scope** per message from natural-language constraints.
- **Source Citations** are evidence. **Trace References** are optional observability, not evidence.
- **Recommendation Status** is AI-generated: Go, No-Go, Validate First.
- **Approval Status** is human review state: Draft, Reviewed, Approved, Rejected.

## Implementation guardrails

- Match existing project patterns before adding new conventions.
- Keep backend FastAPI/Pydantic/SQLModel schemas as the validation source of truth.
- Keep frontend TypeScript types under `apps/web/src/types` by domain.
- Use `/openapi.json` as the frontend/backend contract reference.
- Do not reintroduce `packages/contracts` as active MVP architecture.
- Keep Celery task files thin; place testable business logic in services.
- Use `knowledge/` for retrieval/vector work, not `rag/`.
- Decision Brief Drafts are generated chat artifacts, not final decisions and not a separate MVP page.
- If source-grounded evidence is insufficient, label gaps or assumptions instead of inventing certainty.
