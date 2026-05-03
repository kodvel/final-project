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

export type ChatMessage = {
  id: number
  sessionId: number
  role: ChatMessageRole
  content: string
  messageType: ChatMessageType
  traceId?: string | null
  createdAt: IsoDateTime
}
