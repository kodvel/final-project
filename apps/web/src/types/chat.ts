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
  traceUrl?: string | null
  decisionBriefId?: number | null
  decisionBriefTitle?: string | null
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
  trace_url?: string | null
  decision_brief_id?: number | null
  decision_brief_title?: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
  completed_at?: IsoDateTime | null
}

// ---------------------------------------------------------------------------
// Compound types
// ---------------------------------------------------------------------------

export type ChatSessionDetail = ChatSession & {
  messages: ChatMessage[]
  citations: MessageSourceCitation[]
  toolCalls: AgentToolCall[]
}

export type ChatSessionDetailApi = ChatSessionApi & {
  messages: ChatMessageApi[]
  citations: MessageSourceCitationApi[]
  tool_calls: AgentToolCallApi[]
}

export type CreateChatSessionInput = {
  workspaceId: number
  title?: string
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

export type MetadataEvent = {
  type: 'metadata'
  session_id: number
  assistant_message_id: number | null
  created_session: boolean
  trace_id?: string | null
  trace_url?: string | null
  command?: string | null
}

export type DecisionBriefEvent = {
  type: 'decision_brief'
  message_id: number
  brief_id: number
  sequence_number: number
  recommendation_status: string
  approval_status: string
  title?: string | null
}

export type CommandResultEvent = {
  type: 'command_result'
  message_id: number
  command: string
  ok: boolean
  content: string
}

export type TextDeltaEvent = {
  type: 'text_delta'
  delta: string
}

export type StreamErrorEvent = {
  type: 'error'
  error: string
}

export type ToolCallEvent = {
  type: 'tool_call'
  tool_name: string
  call_id?: string | null
}

export type ToolResultEvent = {
  type: 'tool_result'
  call_id?: string | null
  ok: boolean
}

export type StreamEvent =
  | MetadataEvent
  | TextDeltaEvent
  | StreamErrorEvent
  | ToolCallEvent
  | ToolResultEvent
  | DecisionBriefEvent
  | CommandResultEvent

export type StreamHandlers = {
  onMetadata?: (event: MetadataEvent) => void
  onTextDelta?: (event: TextDeltaEvent) => void
  onError?: (event: StreamErrorEvent) => void
  onToolCall?: (event: ToolCallEvent) => void
  onToolResult?: (event: ToolResultEvent) => void
  onDecisionBrief?: (event: DecisionBriefEvent) => void
  onCommandResult?: (event: CommandResultEvent) => void
  onDone?: () => void
}

// ---------------------------------------------------------------------------
// Tool calls & citations
// ---------------------------------------------------------------------------

export type CitationType = 'uploaded_source' | 'web'
export type CitationStatus = 'available' | 'source_deleted' | 'source_failed' | 'artifact_missing' | 'web_unavailable'

export type AgentToolCall = {
  id: number
  messageId: number
  callId?: string | null
  toolName: string
  status: string
  summary: string
  createdAt?: IsoDateTime | null
}

export type AgentToolCallApi = {
  id: number
  message_id: number
  call_id?: string | null
  tool_name: string
  status: string
  summary: string
  created_at?: IsoDateTime | null
}

export type MessageSourceCitation = {
  id: number
  messageId: number
  sourceId: number | null
  artifactId: number | null
  chunkId: string | null
  citationType: CitationType
  ordinal: number | null
  quote: string | null
  snippet?: string | null
  pageNumber: number | null
  url: string | null
  title: string | null
  domain: string | null
  citationStatus: CitationStatus
  relevanceScore: number | null
  createdAt?: IsoDateTime | null
}

export type MessageSourceCitationApi = {
  id: number
  message_id: number
  source_id: number | null
  artifact_id: number | null
  chunk_id: string | null
  citation_type: CitationType
  ordinal: number | null
  quote: string | null
  snippet?: string | null
  page_number: number | null
  url: string | null
  title: string | null
  domain: string | null
  citation_status: CitationStatus
  relevance_score: number | null
  created_at?: IsoDateTime | null
}
