# Company Intelligence Copilot

Company Intelligence Copilot is a chat-first workspace for turning uploaded company sources into grounded strategic discussion and decision drafts.

## Language

**Workspace**:
A lightweight context/container for source data, visualizations, chat sessions, and decision brief drafts.
_Avoid_: Account, organization, tenant

**Active Workspace**:
The workspace currently selected by the client UI for filtering and scoping API requests.
_Avoid_: Global active workspace, server active workspace

**Source**:
An uploaded company input file plus its metadata, labels, period, processing status, and generated artifacts.
_Avoid_: Source Data as the domain entity

**Source Period**:
A required month-level range on a Source, stored as `period_start_month` and `period_end_month` in `YYYY-MM` format. The display label is derived by the backend.
_Avoid_: User-entered period labels, date-level source periods

**Source Data**:
The product page/menu where users manage Sources.
_Avoid_: Using Source Data to mean one uploaded file

**Processing Status**:
The readiness state of a Source for visualization and chat use: Uploaded, Processing, Ready, or Failed.
_Avoid_: Job status, worker status

**Deleted Source**:
A Source hidden from normal Source Data lists and future retrieval, while retained for citation and decision audit history.
_Avoid_: Permanently removed source

**Source Artifact**:
A normalized knowledge output from processing a Source. Source Artifacts use common types across file formats: `source_summary`, `source_content`, and optional `source_insight`.
_Avoid_: Raw uploaded file, visualization widget

**Source Content**:
The searchable and citation-ready artifact chunks generated from a Source and indexed into ChromaDB when indexable.
_Avoid_: Treating VectorDB as the source of truth

**Source Citation**:
A reference from an assistant answer or Decision Brief Draft back to the Source or Source Artifact that supports it.
_Avoid_: Decorative source link, ungrounded reference

**Source Scope**:
The workspace, team, category, period, or specific Source constraints used to choose evidence for a chat response.
_Avoid_: Permanent chat filter, manual source configuration

**Visualization Data**:
The product page/menu where users inspect a cached, period-based intelligence view composed from ready Source Artifacts.
_Avoid_: Manual BI dashboard, raw data table, per-Source artifact viewer

**Visualization Snapshot**:
A rebuildable cached view for one Workspace and one month range, generated from ready Source Artifacts.
_Avoid_: Source of truth, final report

**Chat Session**:
A conversation thread scoped to exactly one Workspace.
_Avoid_: Workspace-agnostic chat, chat that follows the current workspace after creation

**Decision Brief Draft**:
An AI-generated decision artifact produced from a chat discussion and source evidence, pending human review.
_Avoid_: Final decision, approved decision by default

**Recommendation Status**:
The AI's recommended direction for a Decision Brief Draft: Go, No-Go, or Validate First.
_Avoid_: Approval status

**Approval Status**:
The human review state of a Decision Brief Draft: Draft, Reviewed, Approved, or Rejected.
_Avoid_: AI recommendation status

**Trace Reference**:
An optional observability reference for an AI run, shown when tracing is available but not required for core chat behavior.
_Avoid_: Required chat output, user-facing evidence

## Relationships

- A **Workspace** owns source data, visualizations, chat sessions, and decision brief drafts.
- An **Active Workspace** is client-selected; selecting it in one browser must not change another browser's selected workspace.
- A **Workspace** owns many **Sources**.
- **Source Data** lists and manages **Sources** for the **Active Workspace**.
- A **Source** must have a valid **Source Period**; the start month must be earlier than or equal to the end month.
- A **Source** has one **Processing Status** that tells whether it can be used by Visualization Data and Chat.
- A **Source** can exist before processing succeeds; failed processing does not mean the uploaded Source should disappear.
- A **Deleted Source** is excluded from new analysis but remains available to explain past citations and Decision Brief Drafts.
- A **Deleted Source** may retain its original file when past **Source Citations** or **Decision Brief Drafts** need audit history.
- A **Source** produces normalized **Source Artifacts** after processing.
- A ready **Source** must have a `source_summary` artifact and indexable `source_content` stored in SQL and indexed in ChromaDB; if no citation-ready content can be produced, the Source is **Failed**, not **Ready**.
- `source_insight` is recommended but optional; missing insight should be represented as a warning or gap, not invented certainty.
- **Visualization Data** shows a cached **Visualization Snapshot** for a selected month range, composed from overlapping ready Sources.
- A **Source Citation** supports an assistant answer or **Decision Brief Draft** with a referenced Source, Source Artifact, quote, or page reference where available.
- Chat uses all relevant Sources by default and can narrow **Source Scope** from the user's natural-language request.
- API requests that need workspace scope receive an explicit `workspace_id` from the client-selected **Active Workspace**.
- A **Workspace** owns many **Chat Sessions**.
- A **Chat Session** stays scoped to its original **Workspace** even if the user switches the **Active Workspace** later.
- A **Decision Brief Draft** has one **Recommendation Status** from AI and one independent **Approval Status** from human review.
- A **Trace Reference** may be attached to an assistant message, but missing tracing must not block chat or Decision Brief Draft generation.

## Example dialogue

> **Dev:** "When Demo selects the Demo workspace, should Developer 1's browser switch too?"
> **Domain expert:** "No — the active workspace is only the client-selected workspace for that browser/app session."

> **Dev:** "If a user opens a Demo chat, then switches to Developer 1, should the same chat continue?"
> **Domain expert:** "No — that chat belongs to Demo; Developer 1 needs its own chat session."

> **Dev:** "If AI recommends Validate First, can the user approve the brief?"
> **Domain expert:** "Yes — approval means the draft and its next-step recommendation are accepted for review/action, not that the AI's recommendation changed."

> **Dev:** "If a Source was cited in an approved Decision Brief Draft, can deleting it remove the evidence?"
> **Domain expert:** "No — deleting hides it from future analysis, but past citations must remain explainable."

## Flagged ambiguities

- "active workspace" previously implied a server-persisted global `is_active` flag; resolved: it is client-selected UI state, not global backend state.
- "Source Data" was used for both the page and the uploaded file entity; resolved: **Source** is the entity, **Source Data** is the page/menu.
- Source readiness was mixed with implementation job state; resolved: **Processing Status** describes Source readiness, not Celery worker internals.
- Failed processing was ambiguous with failed upload; resolved: upload can succeed while processing later fails, and the **Source** remains visible for retry or review.
- Deleting a Source could have meant permanent removal; resolved: delete is soft delete so past source-grounded answers remain auditable.
- Soft deletion left file retention unclear; resolved: original files may be removed only when no past citations or Decision Brief Drafts need them for audit.
- Workspace-scoped API requests previously implied server-side activation; resolved: the client sends explicit `workspace_id` instead.
- Chat sessions could have been interpreted as following the selected workspace; resolved: each **Chat Session** is permanently scoped to its original **Workspace**.
- Decision status language was overloaded; resolved: **Recommendation Status** is AI-generated direction, while **Approval Status** is human review state.
- Chat source selection was ambiguous; resolved: Chat auto-selects relevant Sources by default and treats natural-language constraints as per-message **Source Scope**.
- Observability was ambiguous with evidence; resolved: **Trace References** are optional debugging/observability links, while **Source Citations** are evidence.
- CSV-specific artifact names (`csv_profile`, `chart_spec`, `insight_card`) made the product model file-type-driven; resolved: all Source types produce `source_summary`, `source_content`, and optional `source_insight`.
- Visualization was previously treated as a per-Source artifact; resolved: **Visualization Data** is a period-based composed **Visualization Snapshot**.
- Date-level Source periods and manual period labels created too many cache variants; resolved: Sources use `period_start_month` and `period_end_month`, and display labels are derived.
