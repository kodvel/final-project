import type { IsoDateTime } from './common'

export type ChatMessageRole = 'user' | 'assistant' | 'system'
export type ChatMessageType = 'normal' | 'decision_brief' | 'command_result'

export type ChatSession = {
  id: number
  workspaceId: number
  title: string
  createdAt: IsoDateTime
  updatedAt: IsoDateTime
}

export type ChatSessionApi = {
  id: number
  workspace_id: number
  title: string
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export type ChatMessage = {
  id: number
  sessionId: number
  role: ChatMessageRole
  content: string
  messageType: ChatMessageType
  traceId?: string | null
  createdAt: IsoDateTime
}

export type ChatMessageApi = {
  id: number
  session_id: number
  role: ChatMessageRole
  content: string
  message_type: ChatMessageType
  trace_id?: string | null
  created_at: IsoDateTime
}

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
