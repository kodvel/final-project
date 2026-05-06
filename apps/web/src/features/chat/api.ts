import { apiFetch } from '../../lib/api-client'
import type {
  ChatMessage,
  ChatMessageApi,
  ChatMessagePair,
  ChatMessagePairApi,
  ChatSession,
  ChatSessionApi,
  ChatSessionDetail,
  ChatSessionDetailApi,
  CreateChatSessionInput,
  SendChatMessageInput,
} from '../../types/chat'

function messageFromApi(message: ChatMessageApi): ChatMessage {
  return {
    id: message.id,
    sessionId: message.session_id,
    role: message.role,
    content: message.content,
    messageType: message.message_type,
    traceId: message.trace_id,
    createdAt: message.created_at,
  }
}

function sessionFromApi(session: ChatSessionApi): ChatSession {
  return {
    id: session.id,
    workspaceId: session.workspace_id,
    title: session.title,
    createdAt: session.created_at,
    updatedAt: session.updated_at,
  }
}

function sessionDetailFromApi(session: ChatSessionDetailApi): ChatSessionDetail {
  return {
    ...sessionFromApi(session),
    messages: session.messages.map(messageFromApi),
  }
}

export async function createChatSession(input: CreateChatSessionInput): Promise<ChatSession> {
  return sessionFromApi(
    await apiFetch<ChatSessionApi>('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ workspace_id: input.workspaceId, title: input.title }),
    }),
  )
}

export async function listChatSessions(workspaceId: number): Promise<ChatSession[]> {
  const sessions = await apiFetch<ChatSessionApi[]>(`/chat/sessions?workspace_id=${workspaceId}`)
  return sessions.map(sessionFromApi)
}

export async function getChatSession(sessionId: number, workspaceId: number): Promise<ChatSessionDetail> {
  return sessionDetailFromApi(await apiFetch<ChatSessionDetailApi>(`/chat/sessions/${sessionId}?workspace_id=${workspaceId}`))
}

export async function sendChatMessage(input: SendChatMessageInput): Promise<ChatMessagePair> {
  const pair = await apiFetch<ChatMessagePairApi>(`/chat/sessions/${input.sessionId}/messages?workspace_id=${input.workspaceId}`, {
    method: 'POST',
    body: JSON.stringify({ content: input.content }),
  })
  return {
    userMessage: messageFromApi(pair.user_message),
    assistantMessage: messageFromApi(pair.assistant_message),
  }
}
