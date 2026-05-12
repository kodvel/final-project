# ADR 0007: Streaming Chat and Decision Brief Workflow

## Status

Accepted

## Context

The Chat page is the primary product surface for Company Intelligence Copilot. It needs to support GPT-like streaming responses, source-grounded answers, web fallback when local evidence is weak, Chat history, and explicit Decision Brief Draft generation.

Earlier docs assumed a simpler non-streaming Chat endpoint, slash-command status changes, and agent-oriented Decision Brief generation. The current MVP direction is more specific:

- the frontend uses DeltaKit React for chat streaming;
- local uploaded Sources remain the primary evidence source;
- Tavily can provide bounded web evidence only when local evidence is weak or empty and the question is web-answerable;
- Decision Brief Drafts are explicit point-in-time artifacts generated through `/decision-brief`;
- Decision Brief generation should be deterministic workflow orchestration with structured LLM calls, not an autonomous agent workflow for the MVP.
- normal Chat must preserve session continuity without passing unlimited raw conversation history to the model.

## Decision

### Chat streaming

Use DeltaKit-compatible Server-Sent Events for Chat streaming.

The backend streams `text/event-stream` with `data:` JSON lines. Each JSON event has a `type` field. The stream ends with:

```text
data: [DONE]
```

Do not use named SSE `event:` fields for the MVP contract.

The backend uses `StreamingResponse` and manually formats DeltaKit SSE lines. Native browser `EventSource` is not used because the stream endpoint is a POST with a JSON request body. The frontend reads the stream with `fetch` and a `ReadableStream` parser.

OpenAI Agents SDK stream events are internal Python events. The backend converts them into DeltaKit SSE events before sending them to the browser.

Built-in event types:

```text
text_delta
tool_call
tool_result
```

App-specific event types:

```text
session_created
user_message_saved
assistant_started
sources_used
web_sources_used
decision_brief_created
assistant_completed
assistant_interrupted
error
```

`tool_call` events expose only tool name and call ID. `tool_result` events expose status only. Tool errors use safe messages. The stream must not expose private model reasoning, prompts, raw retrieved chunks, Tavily raw results, secrets, or full tool arguments.

### Chat Session creation and history

Chat Sessions are lazily created on the first user message. Opening the Chat page creates only a local draft conversation.

History is Workspace-scoped and initially shows the latest 5 sessions. Show More loads additional sessions by offset.

A Chat Session remains permanently scoped to the Workspace used at creation time. Reopening an old session and sending a new message appends to the same session.

### Chat message lifecycle

Chat stores final message state, not every stream event.

Use message statuses:

```text
pending
streaming
completed
failed
interrupted
```

Partial interrupted assistant content should be retained for audit and UI recovery.

### Context window strategy

Normal Chat is full-session-aware. The backend loads all messages in the Chat Session, then a ContextBuilder creates bounded model context.

The model context is built as:

```text
all session messages
  -> older messages summarized into conversation_summary
  -> recent messages included raw
  -> current user message included raw
```

Recommended MVP settings:

```text
recent_messages_raw = latest 10 messages before current user message
conversation_summary max = 1,000-1,500 tokens
```

Store summary state on `chat_session`:

```text
conversation_summary
summary_cutoff_message_id
summary_updated_at
```

The current user message is always included raw. The summary preserves continuity, but it is not evidence. Internal company factual claims still require uploaded Source citations. Web citations can support external or market context only.

Because Chat also uses RAG, ContextBuilder owns the total prompt budget across conversation history, uploaded Source evidence, optional Tavily web evidence, and reserved output tokens. It must reserve output capacity before prompt assembly.

When budget is tight, preserve context in this priority order:

```text
1. system grounding rules
2. current user message
3. high-quality uploaded Source evidence
4. recent raw messages
5. conversation_summary
6. Tavily web evidence, only when allowed and needed
7. lower-ranked RAG chunks
8. older/redundant raw messages
```

Summary refresh should happen before the context is full, around 70-80% of context capacity.

### Evidence and citations

Chat runs a small classifier before pre-retrieval. If the message needs uploaded company evidence, or if classification fails, Chat retrieves company knowledge from uploaded Sources before answering. The consultant agent still has the retrieval tool available during the run.

Eligible uploaded Sources must be:

```text
same Workspace
processing_status = ready
deleted_at IS NULL
```

ChromaDB is a derived search index. Retrieval candidates must be validated and hydrated through SQL before they become evidence.

RAG evidence must be compact and quality-gated before prompt injection:

```text
ChromaDB candidate search
  -> SQL validation
  -> deduplication
  -> reranking
  -> per-Source diversity cap
  -> retrieval quality gate
  -> compact final EvidenceBundle
```

Normal Chat should receive roughly 8-12 final evidence chunks by default, not unlimited raw candidates or full artifacts. Weak or misleading retrieval results should be marked insufficient rather than injected just to fill the prompt.

To reduce lost-in-the-middle failures, keep evidence compact, avoid excessive chunk counts, and do not bury the strongest evidence in the middle of a long prompt. The current user message should remain near the end of the assembled context.

Only evidence actually used in the final answer is persisted as a citation.

The model should return `used_citation_ids`; the backend must validate that every used citation ID was included in the provided EvidenceBundle before saving citations. Invalid citation IDs must be rejected or repaired before persistence.

The existing citation table may keep the historical name `message_source_citation`, but it must support two citation types:

```text
uploaded_source
web
```

Uploaded Source citations reference `source_data`, `source_artifact`, and optional chunk/page/row metadata. Web citations store URL, title, snippet, provider metadata, and relevance score.

Old citations remain visible for audit even if a Source is later deleted, failed, or reprocessed. The UI should show non-available citations in a warning/disabled state.

### Tavily web fallback

Use Tavily as the MVP web search provider.

Tavily search is allowed only when both conditions are true:

```text
uploaded Source evidence is weak or empty
AND the question is public, current, market-facing, or generally answerable from the web
```

Tavily must not be used to invent internal company facts, answer uploaded Source-specific questions without local evidence, or bypass Workspace boundaries.

Recommended defaults:

```text
max_results = 5
search_depth = basic
include_answer = false
include_raw_content = false
include_images = false
```

Map Tavily result fields into web citations:

```text
title -> title
url -> url
content -> snippet
score -> relevance_score
published_date -> published_date
request_id -> provider_request_id
```

### Decision Brief Draft generation

Decision Brief Draft generation is explicit through `/decision-brief`.

For the MVP, `/decision-brief` uses:

```text
all messages in the current Chat Session
all citations already used in that Chat Session
```

It does not run broad retrieval across all Sources again.

Decision Brief generation can reuse `conversation_summary` for efficiency, but it must remain full-session-aware. For long sessions, it should process messages in chunks and merge structured extraction results rather than silently dropping older decision context.

If there is not enough conversation context or cited evidence, return a clear command result and do not create a Decision Brief Draft:

```text
Belum ada context yang cukup untuk membuat Decision Brief Draft.
Diskusikan keputusan, opsi, risiko, dan evidence terlebih dahulu, lalu jalankan /decision-brief lagi.
```

Decision Brief generation is a deterministic backend workflow using structured LLM calls for:

1. extracting decision context;
2. mapping cited evidence to options, risks, assumptions, and gaps;
3. drafting structured Decision Brief JSON;
4. validating cited evidence IDs in code before persistence.

Each `/decision-brief` creates a new point-in-time draft. Drafts are not overwritten and do not auto-update when conversation continues.

The `decision_brief` record should include:

```text
sequence_number
context_cutoff_message_id
```

### Decision Brief status changes

Decision Brief Approval Status changes from actions on the Decision Brief card in Chat, not through a `/brief-status` command in the MVP.

Allowed transitions:

```text
draft -> reviewed
draft -> approved
draft -> rejected
reviewed -> approved
reviewed -> rejected
approved = locked
rejected = locked
```

Use:

```text
PATCH /decision-briefs/{brief_id}/status
```

## Consequences

- The Chat API centers on `POST /chat/messages/stream` rather than a non-streaming per-session message endpoint.
- DeltaKit event compatibility constrains the SSE wire format to `data:` JSON objects with a `type` field and a `[DONE]` sentinel.
- The ContextBuilder prevents the model from seeing only the latest message while also avoiding unlimited raw history and unlimited RAG chunks.
- RAG evidence competes for the same context budget as conversation history, so retrieval must return compact, validated, quality-gated EvidenceBundles.
- The citation model becomes polymorphic while preserving uploaded Source auditability.
- Tavily web evidence is available, but only as bounded fallback evidence and with explicit Web Source labeling.
- Decision Brief Draft generation remains predictable and testable because the backend owns the workflow steps.
- Re-running `/decision-brief` in the same Chat Session creates a new draft, preserving point-in-time audit history.
- Status changes are visible user actions on the Decision Brief card instead of hidden slash-command state changes.

## Alternatives considered

### Native EventSource GET stream

Rejected for MVP because Chat message submission needs a POST body with `workspace_id`, optional `session_id`, and message content.

### Named SSE `event:` fields

Rejected because DeltaKit's documented parser expects `data:` JSON events with a `type` field and a `[DONE]` sentinel.

### WebSocket streaming

Rejected for MVP because Chat streaming is mostly server-to-client. SSE is simpler and fits DeltaKit.

### Tavily for every answer

Rejected because uploaded Sources are the primary company evidence. Web search is only a fallback for public/current questions with weak local evidence.

### Passing all raw messages to the model forever

Rejected because long sessions can exceed token limits, increase cost, and distract the model. The accepted approach summarizes older messages and keeps recent turns raw.

### Passing only the latest user message

Rejected because it loses conversation continuity and makes the assistant ignore prior user goals, constraints, and decisions.

### Passing all retrieved RAG chunks to the model

Rejected because retrieved evidence shares the same context budget as conversation history. Unlimited chunks increase cost, worsen lost-in-the-middle behavior, and can make weak evidence look more important than it is. The accepted approach injects only compact, validated, reranked, quality-gated EvidenceBundle items.

### Autonomous Decision Brief agent

Rejected for MVP. A deterministic workflow with structured LLM calls is easier to test, audit, and align with the product's point-in-time Decision Brief Draft semantics.

### Overwriting the latest Decision Brief Draft

Rejected because it destroys audit history. Each `/decision-brief` run creates a new draft.

### `/brief-status` slash command

Rejected for MVP UX. Status changes should be explicit actions on the Decision Brief card.
