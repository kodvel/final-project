import { API_BASE_URL, apiFetch } from '../../lib/api-client'
import type {
  AgentToolCall,
  AgentToolCallApi,
  AssistantCompletedEvent,
  AssistantStartedEvent,
  ChatMessage,
  ChatMessageApi,
  ChatSession,
  ChatSessionApi,
  ChatSessionDetail,
  ChatSessionDetailApi,
  CreateChatSessionInput,
  MessageSourceCitation,
  MessageSourceCitationApi,
  SendChatMessageInput,
  SessionCreatedEvent,
  SourcesUsedEvent,
  StreamChatMessageInput,
  StreamErrorEvent,
  StreamHandlers,
  TextDeltaEvent,
  ToolCallEvent,
  ToolResultEvent,
  UserMessageSavedEvent,
  WebSourcesUsedEvent,
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
// Legacy CRUD
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

// ---------------------------------------------------------------------------
// Legacy JSON send (kept for reference; prefer streamChatMessage)
// ---------------------------------------------------------------------------

export async function sendChatMessage(input: SendChatMessageInput): Promise<{ userMessage: ChatMessage; assistantMessage: ChatMessage }> {
  const pair = await apiFetch<{ user_message: ChatMessageApi; assistant_message: ChatMessageApi }>(
    `/chat/sessions/${input.sessionId}/messages?workspace_id=${input.workspaceId}`,
    {
      method: 'POST',
      body: JSON.stringify({ content: input.content }),
    },
  )
  return {
    userMessage: messageFromApi(pair.user_message),
    assistantMessage: messageFromApi(pair.assistant_message),
  }
}

// ---------------------------------------------------------------------------
// SSE streaming
// ---------------------------------------------------------------------------

/**
 * Send a chat message via the SSE stream endpoint and dispatch parsed events
 * to the provided handlers. Returns a promise that resolves when the stream
 * ends (either `[DONE]` sentinel or the reader closes).
 */
export async function streamChatMessage(input: StreamChatMessageInput, handlers: StreamHandlers): Promise<void> {
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
        const lines = part.split('\n')
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') return

          try {
            const event = JSON.parse(payload) as { type: string }
            switch (event.type) {
              case 'session_created':
                handlers.onSessionCreated?.(event as SessionCreatedEvent)
                break
              case 'user_message_saved':
                handlers.onUserMessageSaved?.(event as UserMessageSavedEvent)
                break
              case 'assistant_started':
                handlers.onAssistantStarted?.(event as AssistantStartedEvent)
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
              case 'sources_used':
                handlers.onSourcesUsed?.(event as SourcesUsedEvent)
                break
              case 'web_sources_used':
                handlers.onWebSourcesUsed?.(event as WebSourcesUsedEvent)
                break
              case 'assistant_completed':
                handlers.onAssistantCompleted?.(event as AssistantCompletedEvent)
                break
              case 'error':
                handlers.onError?.(event as StreamErrorEvent)
                break
            }
          } catch {
            // Ignore malformed JSON lines
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
