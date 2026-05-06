import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createChatSession, getChatSession, listChatSessions, sendChatMessage } from '../api'

export function useChatSessions(workspaceId: number | null) {
  return useQuery({
    queryKey: ['chat-sessions', workspaceId],
    queryFn: () => listChatSessions(workspaceId ?? 0),
    enabled: typeof workspaceId === 'number' && workspaceId > 0,
  })
}

export function useChatSession(sessionId: number | null, workspaceId: number | null) {
  return useQuery({
    queryKey: ['chat-session', sessionId, workspaceId],
    queryFn: () => getChatSession(sessionId ?? 0, workspaceId ?? 0),
    enabled: typeof sessionId === 'number' && sessionId > 0 && typeof workspaceId === 'number' && workspaceId > 0,
  })
}

export function useCreateChatSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createChatSession,
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions', session.workspaceId] })
    },
  })
}

export function useSendChatMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (_pair, input) => {
      queryClient.invalidateQueries({ queryKey: ['chat-session', input.sessionId, input.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
    },
  })
}
