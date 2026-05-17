import { API_BASE_URL, apiFetch } from '../../lib/api-client'
import type {
  AgentToolCall,
  AgentToolCallApi,
  ChatMessage,
  ChatMessageApi,
  ChatSession,
  ChatSessionApi,
  ChatSessionDetail,
  ChatSessionDetailApi,
  CommandResultEvent,
  CreateChatSessionInput,
  DecisionBriefEvent,
  MessageSourceCitation,
  MessageSourceCitationApi,
  MetadataEvent,
  StreamChatMessageInput,
  StreamErrorEvent,
  StreamHandlers,
  TextDeltaEvent,
  ToolCallEvent,
  ToolResultEvent,
} from '../../types/chat'

function messageFromApi(message: ChatMessageApi): ChatMessage {
  return {
    id: message.id,
    sessionId: message.session_id,
    role: message.role,
    content: message.content,
    messageType: message.message_type,
    status: message.status,
    errorMessage: message.error_message,
    metadataJson: message.metadata_json,
    traceId: message.trace_id,
    traceUrl: message.trace_url,
    decisionBriefId: message.decision_brief_id ?? null,
    decisionBriefTitle: message.decision_brief_title ?? null,
    createdAt: message.created_at,
    updatedAt: message.updated_at,
    completedAt: message.completed_at,
  }
}

function sessionFromApi(session: ChatSessionApi): ChatSession {
  return {
    id: session.id,
    workspaceId: session.workspace_id,
    title: session.title,
    createdAt: session.created_at,
    updatedAt: session.updated_at,
    lastMessageAt: session.last_message_at,
    conversationSummary: session.conversation_summary,
    summaryCutoffMessageId: session.summary_cutoff_message_id,
    summaryUpdatedAt: session.summary_updated_at,
  }
}

function toolCallFromApi(toolCall: AgentToolCallApi): AgentToolCall {
  return {
    id: toolCall.id,
    messageId: toolCall.message_id,
    callId: toolCall.call_id,
    toolName: toolCall.tool_name,
    status: toolCall.status,
    summary: toolCall.summary,
    createdAt: toolCall.created_at,
  }
}

function citationFromApi(citation: MessageSourceCitationApi): MessageSourceCitation {
  return {
    id: citation.id,
    messageId: citation.message_id,
    sourceId: citation.source_id,
    artifactId: citation.artifact_id,
    chunkId: citation.chunk_id,
    citationType: citation.citation_type,
    ordinal: citation.ordinal,
    quote: citation.quote,
    snippet: citation.snippet,
    pageNumber: citation.page_number,
    url: citation.url,
    title: citation.title,
    domain: citation.domain,
    citationStatus: citation.citation_status,
    relevanceScore: citation.relevance_score,
    createdAt: citation.created_at,
  }
}

function sessionDetailFromApi(session: ChatSessionDetailApi): ChatSessionDetail {
  return {
    ...sessionFromApi(session),
    messages: session.messages.map(messageFromApi),
    citations: (session.citations ?? []).map(citationFromApi),
    toolCalls: (session.tool_calls ?? []).map(toolCallFromApi),
  }
}

// ---------------------------------------------------------------------------
// CRUD
// ---------------------------------------------------------------------------

export async function createChatSession(input: CreateChatSessionInput): Promise<ChatSession> {
  return sessionFromApi(
    await apiFetch<ChatSessionApi>('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ workspace_id: input.workspaceId, title: input.title }),
    }),
  )
}

export async function listChatSessions(workspaceId: number, limit = 5, offset = 0): Promise<ChatSession[]> {
  const sessions = await apiFetch<ChatSessionApi[]>(`/chat/sessions?workspace_id=${workspaceId}&limit=${limit}&offset=${offset}`)
  return sessions.map(sessionFromApi)
}

export async function getChatSession(sessionId: number, workspaceId: number): Promise<ChatSessionDetail> {
  return sessionDetailFromApi(await apiFetch<ChatSessionDetailApi>(`/chat/sessions/${sessionId}?workspace_id=${workspaceId}`))
}

/**
 * Send a chat message via the SSE stream endpoint and dispatch parsed events
 * to the provided handlers. Returns a promise that resolves when the stream
 * ends (either `[DONE]` sentinel or the reader closes).
 */
export async function streamChatMessage(input: StreamChatMessageInput, handlers: StreamHandlers, signal?: AbortSignal): Promise<void> {
  const body: Record<string, unknown> = {
    workspace_id: input.workspaceId,
    message: input.message,
  }
  if (input.sessionId != null) {
    body.session_id = input.sessionId
  }

  const response = await fetch(`${API_BASE_URL}/chat/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    const text = await response.text()
    const errorMsg = text || `Stream request failed: ${response.status}`
    handlers.onError?.({ type: 'error', error: errorMsg })
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    handlers.onError?.({ type: 'error', error: 'No readable stream' })
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false

  // Returns true when [DONE] was seen, so the caller can stop reading.
  const processPart = (part: string): boolean => {
    for (const line of part.split('\n')) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (payload === '[DONE]') {
        completed = true
        handlers.onDone?.()
        return true
      }

      try {
        const event = JSON.parse(payload) as { type: string }
        switch (event.type) {
          case 'metadata':
            handlers.onMetadata?.(event as MetadataEvent)
            break
          case 'text_delta':
            handlers.onTextDelta?.(event as TextDeltaEvent)
            break
          case 'tool_call':
            handlers.onToolCall?.(event as ToolCallEvent)
            break
          case 'tool_result':
            handlers.onToolResult?.(event as ToolResultEvent)
            break
          case 'decision_brief':
            handlers.onDecisionBrief?.(event as DecisionBriefEvent)
            break
          case 'command_result':
            handlers.onCommandResult?.(event as CommandResultEvent)
            break
          case 'error':
            handlers.onError?.(event as StreamErrorEvent)
            break
        }
      } catch {
        // Ignore malformed JSON lines
      }
    }
    return false
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE lines are separated by double newlines; process complete chunks
      const parts = buffer.split('\n\n')
      // Keep the last (potentially incomplete) part in the buffer
      buffer = parts.pop() ?? ''

      for (const part of parts) {
        if (processPart(part)) return
      }
    }

    // Flush any remaining buffered content (e.g. final `data: [DONE]` that
    // didn't arrive with a trailing \n\n before EOF).
    if (buffer.length > 0) {
      processPart(buffer)
      buffer = ''
    }

    if (!completed) {
      handlers.onError?.({ type: 'error', error: 'Stream closed before completion' })
    }
  } finally {
    reader.releaseLock()
  }
}
