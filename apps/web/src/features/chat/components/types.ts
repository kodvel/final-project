import type { ChatMessage, MessageSourceCitation } from '../../../types/chat'

// ---------------------------------------------------------------------------
// Optimistic message types (local-only, never persisted as-is)
// ---------------------------------------------------------------------------

export type OptimisticUserMessage = {
  __optimistic: true
  id: string
  role: 'user'
  content: string
}

export type OptimisticAssistantMessage = {
  __optimistic: true
  id: string
  role: 'assistant'
  content: string
}

export type StreamingToolCall = {
  callId: string
  toolName: string
  status: 'running' | 'done' | 'failed'
}

export type DisplayMessage = ChatMessage | OptimisticUserMessage | OptimisticAssistantMessage

export function isOptimistic(msg: DisplayMessage): msg is OptimisticUserMessage | OptimisticAssistantMessage {
  return '__optimistic' in msg && msg.__optimistic === true
}

// ---------------------------------------------------------------------------
// Citation grouping
// ---------------------------------------------------------------------------

export type CitationGroup = {
  key: string
  title: string
  badge: string
  citations: MessageSourceCitation[]
}
