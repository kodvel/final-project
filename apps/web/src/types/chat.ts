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
