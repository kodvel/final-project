import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'
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
  const [isStreaming, setIsStreaming] = useState(false)

  const sendMessage = useCallback(
    async (input: StreamChatMessageInput, handlers: StreamHandlers) => {
      // Abort any in-flight stream
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      setIsStreaming(true)

      // Track the actual session ID — may differ from input.sessionId when
      // the backend lazily creates a new session mid-stream.
      let resolvedSessionId: number | null = input.sessionId ?? null

      const wrappedHandlers: StreamHandlers = {
        ...handlers,
        onMetadata: (event) => {
          resolvedSessionId = event.session_id
          handlers.onMetadata?.(event)
        },
        onDone: () => {
          handlers.onDone?.()
          // Refetch session detail + session list after streaming completes.
          // Use the resolved session ID (covers lazy-created sessions).
          const sid = resolvedSessionId
          if (sid != null) {
            queryClient.invalidateQueries({ queryKey: ['chat-session', sid, input.workspaceId] })
          }
          queryClient.invalidateQueries({ queryKey: ['chat-sessions', input.workspaceId] })
          setIsStreaming(false)
        },
        onError: (event) => {
          handlers.onError?.(event)
          const sid = resolvedSessionId
          if (sid != null) {
            queryClient.invalidateQueries({ queryKey: ['chat-session', sid, input.workspaceId] })
          }
          queryClient.invalidateQueries({ queryKey: ['chat-sessions', input.workspaceId] })
          setIsStreaming(false)
        },
      }

      try {
        await streamChatMessage(input, wrappedHandlers, controller.signal)
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          const sid = resolvedSessionId
          if (sid != null) {
            queryClient.invalidateQueries({ queryKey: ['chat-session', sid, input.workspaceId] })
          }
          queryClient.invalidateQueries({ queryKey: ['chat-sessions', input.workspaceId] })
          return
        }
        setIsStreaming(false)
        wrappedHandlers.onError?.({ type: 'error', error: err instanceof Error ? err.message : 'Stream failed' })
      }
    },
    [queryClient],
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return { sendMessage, abort, isStreaming }
}
