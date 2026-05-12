import type { IsoDateTime } from './common'

export type ChatMessageRole = 'user' | 'assistant' | 'system'
export type ChatMessageType = 'normal' | 'decision_brief' | 'command_result'
export type MessageStatus = 'pending' | 'streaming' | 'completed' | 'failed' | 'interrupted'

// ---------------------------------------------------------------------------
// Session types
// ---------------------------------------------------------------------------

export type ChatSession = {
  id: number
  workspaceId: number
  title: string
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
  lastMessageAt?: IsoDateTime | null
  conversationSummary?: string | null
  summaryCutoffMessageId?: number | null
  summaryUpdatedAt?: IsoDateTime | null
}

export type ChatSessionApi = {
  id: number
  workspace_id: number
  title: string
  created_at: IsoDateTime
  updated_at: IsoDateTime
  last_message_at?: IsoDateTime | null
  conversation_summary?: string | null
  summary_cutoff_message_id?: number | null
  summary_updated_at?: IsoDateTime | null
}

// ---------------------------------------------------------------------------
// Message types
// ---------------------------------------------------------------------------

export type ChatMessage = {
  id: number
  sessionId: number
  role: ChatMessageRole
  content: string
  messageType: ChatMessageType
  status: MessageStatus
  errorMessage?: string | null
  metadataJson?: Record<string, unknown> | null
  traceId?: string | null
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
  completedAt?: IsoDateTime | null
}

export type ChatMessageApi = {
  id: number
  session_id: number
  role: ChatMessageRole
  content: string
  message_type: ChatMessageType
  status: MessageStatus
  error_message?: string | null
  metadata_json?: Record<string, unknown> | null
  trace_id?: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
  completed_at?: IsoDateTime | null
}

// ---------------------------------------------------------------------------
// Compound types
// ---------------------------------------------------------------------------

export type ChatSessionDetail = ChatSession & {
  messages: ChatMessage[]
}

export type ChatSessionDetailApi = ChatSessionApi & {
  messages: ChatMessageApi[]
}

export type CreateChatSessionInput = {
  workspaceId: number
  title?: string
}

export type SendChatMessageInput = {
  sessionId: number
  workspaceId: number
  content: string
}

export type ChatMessagePair = {
  userMessage: ChatMessage
  assistantMessage: ChatMessage
}

export type ChatMessagePairApi = {
  user_message: ChatMessageApi
  assistant_message: ChatMessageApi
}

// ---------------------------------------------------------------------------
// Stream input
// ---------------------------------------------------------------------------

export type StreamChatMessageInput = {
  workspaceId: number
  sessionId?: number | null
  message: string
}

// ---------------------------------------------------------------------------
// Stream event types (discriminated union on `type`)
// ---------------------------------------------------------------------------

export type SessionCreatedEvent = {
  type: 'session_created'
  session: ChatSessionApi
}

export type UserMessageSavedEvent = {
  type: 'user_message_saved'
  message: ChatMessageApi
}

export type AssistantStartedEvent = {
  type: 'assistant_started'
  message: ChatMessageApi
}

export type TextDeltaEvent = {
  type: 'text_delta'
  delta: string
}

export type AssistantCompletedEvent = {
  type: 'assistant_completed'
  message: ChatMessageApi
}

export type StreamErrorEvent = {
  type: 'error'
  error: string
}

export type StreamEvent =
  | SessionCreatedEvent
  | UserMessageSavedEvent
  | AssistantStartedEvent
  | TextDeltaEvent
  | AssistantCompletedEvent
  | StreamErrorEvent

export type StreamHandlers = {
  onSessionCreated?: (event: SessionCreatedEvent) => void
  onUserMessageSaved?: (event: UserMessageSavedEvent) => void
  onAssistantStarted?: (event: AssistantStartedEvent) => void
  onTextDelta?: (event: TextDeltaEvent) => void
  onAssistantCompleted?: (event: AssistantCompletedEvent) => void
  onError?: (event: StreamErrorEvent) => void
}

// ---------------------------------------------------------------------------
// Tool calls & citations (minimal for now)
// ---------------------------------------------------------------------------

export type AgentToolCall = {
  id: number
  messageId: number
  toolName: string
  status: string
  summary: string
  createdAt: IsoDateTime
}

export type AgentToolCallApi = {
  id: number
  message_id: number
  tool_name: string
  status: string
  summary: string
  created_at: IsoDateTime
}

export type MessageSourceCitation = {
  id: number
  messageId: number
  sourceId: number
  artifactId?: number | null
  quote?: string | null
  pageNumber?: number | null
  createdAt: IsoDateTime
}

export type MessageSourceCitationApi = {
  id: number
  message_id: number
  source_id: number
  artifact_id?: number | null
  quote?: string | null
  page_number?: number | null
  created_at: IsoDateTime
}
