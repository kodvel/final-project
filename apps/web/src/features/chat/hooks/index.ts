import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef } from 'react'
import type { StreamChatMessageInput, StreamHandlers } from '../../../types/chat'
import { getChatSession, listChatSessions, streamChatMessage } from '../api'

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

/**
 * Hook that returns a `sendMessage` callback which calls the SSE stream endpoint
 * and dispatches events to the provided handlers. Manages abort via a ref so that
 * only one stream can be active at a time.
 */
export function useStreamChat() {
  const queryClient = useQueryClient()
  const abortRef = useRef<AbortController | null>(null)
  const streamingRef = useRef(false)

  const sendMessage = useCallback(
    async (input: StreamChatMessageInput, handlers: StreamHandlers) => {
      // Abort any in-flight stream
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      streamingRef.current = true

      const wrappedHandlers: StreamHandlers = {
        ...handlers,
        onAssistantCompleted: (event) => {
          handlers.onAssistantCompleted?.(event)
          // Refetch session detail + session list after streaming completes
          const sid = input.sessionId
          if (sid != null) {
            queryClient.invalidateQueries({ queryKey: ['chat-session', sid, input.workspaceId] })
          }
          queryClient.invalidateQueries({ queryKey: ['chat-sessions', input.workspaceId] })
          streamingRef.current = false
        },
        onError: (event) => {
          handlers.onError?.(event)
          streamingRef.current = false
        },
      }

      try {
        await streamChatMessage(input, wrappedHandlers)
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        streamingRef.current = false
        wrappedHandlers.onError?.({ type: 'error', error: err instanceof Error ? err.message : 'Stream failed' })
      }
    },
    [queryClient],
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
    streamingRef.current = false
  }, [])

  return { sendMessage, abort, isStreaming: streamingRef }
}

/** Re-export the message helper for building optimistic messages in the page. */
export { streamChatMessage } from '../api'
