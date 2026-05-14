import { createFileRoute } from '@tanstack/react-router'
import { Send, X } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import type { DisplayMessage, StreamingToolCall } from '../features/chat/components'
import {
  AssistantMessage,
  CommandChip,
  CommandResultMessage,
  EmptyChatState,
  formatDate,
  isOptimistic,
  SourcesPanel,
  UserBubble,
} from '../features/chat/components'
import { useChatSession, useChatSessions, useCreateChatSession, useStreamChat } from '../features/chat/hooks'
import { DecisionBriefCard } from '../features/decision-briefs/components/DecisionBriefCard'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { ChatMessage } from '../types/chat'

export const Route = createFileRoute('/chat')({
  component: ChatPage,
})

// ---------------------------------------------------------------------------
// Chat Page
// ---------------------------------------------------------------------------

export function ChatPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? null
  const { data: sessions = [], isLoading: isLoadingSessions, error: sessionsError } = useChatSessions(workspaceId)
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const { data: activeSession, isLoading: isLoadingSession } = useChatSession(activeSessionId, workspaceId)
  const { mutateAsync: createChatSession, isPending: isCreatingSession } = useCreateChatSession()
  const { sendMessage, abort, isStreaming } = useStreamChat()

  const [input, setInput] = useState('')
  const [isDraftNewChat, setIsDraftNewChat] = useState(false)
  const [isThinking, setIsThinking] = useState(false)
  const [optimisticMessages, setOptimisticMessages] = useState<DisplayMessage[]>([])
  const [streamingText, setStreamingText] = useState('')
  const [streamingToolCalls, setStreamingToolCalls] = useState<StreamingToolCall[]>([])
  const optIdCounter = useRef(0)
  const streamingTextRef = useRef('')
  const chatEndRef = useRef<HTMLDivElement>(null)
  const scrollFrameRef = useRef<number | null>(null)
  const previousScrollStateRef = useRef<{ sessionId: number | null; messageCount: number }>({ sessionId: null, messageCount: 0 })

  const persistedMessages: ChatMessage[] = (activeSession?.messages ?? []).filter(
    (message) => !(isThinking && message.role === 'assistant' && message.status === 'streaming'),
  )

  // Compose displayed messages: persisted + any optimistic that aren't replaced yet
  const messages: DisplayMessage[] = [
    ...persistedMessages,
    ...optimisticMessages.filter((om) => !isOptimistic(om) || !persistedMessages.some((pm) => pm.content === om.content && pm.role === om.role)),
  ]

  // If we have streaming text, append a streaming assistant message
  const streamingMessage = isThinking
    ? { __optimistic: true as const, id: 'opt-streaming-assistant', role: 'assistant' as const, content: streamingText }
    : null
  const displayMessages: DisplayMessage[] = streamingMessage ? [...messages, streamingMessage] : messages
  const hasSessionCitations = (activeSession?.citations.length ?? 0) > 0
  const scrollMessageCount = displayMessages.length
  const scrollTargetKey = `${activeSessionId ?? 'draft'}:${scrollMessageCount}:${streamingText.length}:${streamingToolCalls.length}:${isLoadingSession ? 'loading' : 'ready'}`

  // Reset on workspace change
  useEffect(() => {
    if (activeSession && activeSession.workspaceId !== workspaceId) {
      setActiveSessionId(null)
      setIsDraftNewChat(false)
      setOptimisticMessages([])
      setStreamingText('')
      streamingTextRef.current = ''
      setStreamingToolCalls([])
    }
  }, [activeSession, workspaceId])

  // Auto-select first session
  useEffect(() => {
    if (activeSessionId === null && sessions.length > 0 && !isDraftNewChat) {
      setActiveSessionId(sessions[0].id)
    }
  }, [activeSessionId, sessions, isDraftNewChat])

  useEffect(() => {
    void scrollTargetKey

    const previous = previousScrollStateRef.current
    const shouldAnimate = previous.sessionId !== activeSessionId || scrollMessageCount > previous.messageCount
    previousScrollStateRef.current = { sessionId: activeSessionId, messageCount: scrollMessageCount }

    if (scrollFrameRef.current != null) {
      window.cancelAnimationFrame(scrollFrameRef.current)
    }

    scrollFrameRef.current = window.requestAnimationFrame(() => {
      chatEndRef.current?.scrollIntoView({ behavior: shouldAnimate ? 'smooth' : 'auto', block: 'end' })
    })

    return () => {
      if (scrollFrameRef.current != null) {
        window.cancelAnimationFrame(scrollFrameRef.current)
      }
    }
  }, [scrollTargetKey, activeSessionId, scrollMessageCount])

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      const value = input.trim()
      if (!value || isThinking || !workspaceId) return

      const userOptId = `opt-user-${++optIdCounter.current}` as const

      // Optimistically render user message only; streaming text serves as the assistant placeholder
      setOptimisticMessages((prev) => [...prev, { __optimistic: true, id: userOptId, role: 'user', content: value }])
      setStreamingText('')
      streamingTextRef.current = ''
      setStreamingToolCalls([])
      setIsThinking(true)
      setInput('')

      await sendMessage(
        {
          workspaceId,
          sessionId: activeSessionId,
          message: value,
        },
        {
          onMetadata: (event) => {
            setActiveSessionId(event.session_id)
            setIsDraftNewChat(false)
          },
          onTextDelta: (event) => {
            streamingTextRef.current += event.delta
            setStreamingText(streamingTextRef.current)
          },
          onToolCall: (event) => {
            const callId = event.call_id || `${event.tool_name}-${Date.now()}`
            setStreamingToolCalls((prev) => [...prev, { callId, toolName: event.tool_name, status: 'running' }])
          },
          onToolResult: (event) => {
            if (!event.call_id) return
            setStreamingToolCalls((prev) =>
              prev.map((tool) => (tool.callId === event.call_id ? { ...tool, status: event.ok ? 'done' : 'failed' } : tool)),
            )
          },
          onDecisionBrief: () => {
            // Backend has persisted the Decision Brief assistant message; clear
            // optimistic streaming state so the refetched session renders the
            // brief card cleanly.
            setStreamingText('')
            streamingTextRef.current = ''
            setStreamingToolCalls([])
          },
          onCommandResult: () => {
            setStreamingText('')
            streamingTextRef.current = ''
            setStreamingToolCalls([])
          },
          onDone: () => {
            // Refetch happens inside useStreamChat; clear optimistic state
            const finalStreamedText = streamingTextRef.current
            if (finalStreamedText.trim()) {
              setOptimisticMessages((prev) => [
                ...prev,
                { __optimistic: true, id: `opt-assistant-${++optIdCounter.current}`, role: 'assistant', content: finalStreamedText },
              ])
            }
            setStreamingText('')
            streamingTextRef.current = ''
            setStreamingToolCalls([])
            setIsThinking(false)
          },
          onError: (event) => {
            console.error('Stream error:', event.error)
            const finalStreamedText = streamingTextRef.current
            if (finalStreamedText.trim()) {
              setOptimisticMessages((prev) => [
                ...prev,
                { __optimistic: true, id: `opt-assistant-${++optIdCounter.current}`, role: 'assistant', content: finalStreamedText },
              ])
            }
            setStreamingText('')
            streamingTextRef.current = ''
            setStreamingToolCalls([])
            setIsThinking(false)
            setInput((current) => (current.trim() ? current : value))
          },
        },
      )
    },
    [input, isThinking, workspaceId, activeSessionId, sendMessage],
  )

  async function handleNewChat() {
    abort()
    setIsThinking(false)
    setActiveSessionId(null)
    setIsDraftNewChat(true)
    setOptimisticMessages([])
    setStreamingText('')
    streamingTextRef.current = ''
    setStreamingToolCalls([])
    if (!workspaceId) return
    try {
      const session = await createChatSession({ workspaceId })
      setActiveSessionId(session.id)
      setIsDraftNewChat(false)
    } catch (error) {
      console.error('Failed to create chat session:', error)
    }
  }

  function handleStop() {
    abort()
    setIsThinking(false)
  }

  return (
    <div className={`grid h-full min-h-0 ${hasSessionCitations ? 'grid-cols-[minmax(0,1fr)_376px]' : 'grid-cols-1'} overflow-hidden text-foreground`}>
      <section className="flex min-h-0 min-w-0 flex-col border-r border-border">
        <div className="min-h-0 flex-1 scroll-smooth overflow-y-auto px-10 py-8">
          <div className="mb-7 flex items-center justify-center gap-4">
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-text-hint">
              {activeSession ? `Session started: ${formatDate(activeSession.createdAt)}` : 'Start a Workspace-scoped Chat Session'}
            </p>
            {activeWorkspace && (
              <>
                {!hasSessionCitations && sessions.length > 0 && (
                  <select
                    value={activeSessionId ?? ''}
                    onChange={(event) => {
                      const value = event.target.value
                      if (!value) {
                        handleNewChat()
                        return
                      }
                      setIsDraftNewChat(false)
                      setActiveSessionId(Number(value))
                    }}
                    className="max-w-48 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground outline-none hover:bg-surface-subtle"
                    aria-label="Select Chat Session"
                  >
                    <option value="">New Chat</option>
                    {sessions.map((session) => (
                      <option key={session.id} value={session.id}>
                        {session.title}
                      </option>
                    ))}
                  </select>
                )}
                <button
                  type="button"
                  onClick={handleNewChat}
                  disabled={!activeWorkspace || isCreatingSession}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-surface-subtle"
                >
                  New Chat
                </button>
              </>
            )}
          </div>

          <div className="mx-auto max-w-[850px] space-y-8">
            {!activeWorkspace ? (
              <EmptyChatState
                title="Select a Workspace"
                description="Choose or create a Workspace from the bottom-left switcher before starting Chat."
              />
            ) : sessionsError ? (
              <EmptyChatState title="Could not load Chat" description="Check that the API is running, then try again." />
            ) : isLoadingSessions || isLoadingSession ? (
              <EmptyChatState title="Loading Chat" description="Fetching persisted Chat Sessions and messages." />
            ) : displayMessages.length === 0 ? (
              <EmptyChatState title="Ask a strategic question" description="Messages will be persisted to this Workspace-scoped Chat Session." />
            ) : (
              displayMessages.map((message) => {
                if (message.role === 'user') {
                  return <UserBubble key={message.id} content={message.content} />
                }
                if (!isOptimistic(message) && message.messageType === 'decision_brief' && message.decisionBriefId && workspaceId) {
                  return <DecisionBriefCard key={message.id} briefId={message.decisionBriefId} workspaceId={workspaceId} />
                }
                if (!isOptimistic(message) && message.messageType === 'command_result') {
                  return <CommandResultMessage key={message.id} content={message.content} />
                }
                return (
                  <AssistantMessage
                    key={message.id}
                    message={message}
                    citations={!isOptimistic(message) ? (activeSession?.citations.filter((citation) => citation.messageId === message.id) ?? []) : []}
                    toolCalls={!isOptimistic(message) ? (activeSession?.toolCalls.filter((toolCall) => toolCall.messageId === message.id) ?? []) : []}
                    streamingToolCalls={isOptimistic(message) ? streamingToolCalls : []}
                    showThinking={isOptimistic(message) && isThinking && !streamingText}
                  />
                )
              })
            )}
            <div ref={chatEndRef} aria-hidden="true" />
          </div>
        </div>

        <form onSubmit={handleSubmit} className="shrink-0 border-t border-border bg-card px-8 py-5">
          <div className="mx-auto max-w-[850px]">
            <div className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3 shadow-sm">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask a strategic question or type '/'"
                className="min-w-0 flex-1 border-0 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
              {isStreaming || isThinking ? (
                <button
                  type="button"
                  onClick={handleStop}
                  className="grid h-10 w-10 place-items-center rounded-xl bg-foreground text-card transition hover:bg-foreground/90"
                  aria-label="Stop response"
                >
                  <X className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim() || !activeWorkspace}
                  className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                  aria-label="Send message"
                >
                  <Send className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="mt-3 flex items-center gap-3 text-xs text-text-hint">
              <CommandChip command="/decision-brief" label="Generate Brief" onClick={() => setInput('/decision-brief')} />
              <span className="ml-auto">Copilot can make mistakes. Consider verifying.</span>
            </div>
          </div>
        </form>
      </section>

      {hasSessionCitations && (
        <SourcesPanel
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={(id) => {
            setIsDraftNewChat(false)
            setActiveSessionId(id)
          }}
          citations={activeSession?.citations ?? []}
          toolCalls={activeSession?.toolCalls ?? []}
        />
      )}
    </div>
  )
}
