import { createFileRoute } from '@tanstack/react-router'
import { Send, X } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import type { DisplayMessage, SlashCommand, StreamingToolCall } from '../features/chat/components'
import {
  AssistantMessage,
  CommandChip,
  CommandResultMessage,
  EmptyChatState,
  filterCommands,
  formatDate,
  isOptimistic,
  SlashCommandMenu,
  SourcesPanel,
  UserBubble,
} from '../features/chat/components'
import { useChatSession, useChatSessions, useStreamChat } from '../features/chat/hooks'
import { DecisionBriefCard } from '../features/decision-briefs/components/DecisionBriefCard'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { ChatMessage } from '../types/chat'

export const Route = createFileRoute('/chat')({
  component: ChatPage,
})

// ---------------------------------------------------------------------------
// Session-scoped streaming state
// ---------------------------------------------------------------------------

type SessionKey = number | 'draft'

type SessionStreamingState = {
  optimisticMessages: DisplayMessage[]
  streamingText: string
  streamingToolCalls: StreamingToolCall[]
}

function emptyStreamingState(): SessionStreamingState {
  return { optimisticMessages: [], streamingText: '', streamingToolCalls: [] }
}

// ---------------------------------------------------------------------------
// Chat Page
// ---------------------------------------------------------------------------

export function ChatPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? null
  const { data: sessions = [], isLoading: isLoadingSessions, error: sessionsError } = useChatSessions(workspaceId)
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const { data: activeSession, isLoading: isLoadingSession } = useChatSession(activeSessionId, workspaceId)
  const { sendMessage, abort, isStreaming } = useStreamChat()

  const [input, setInput] = useState('')
  const [isDraftNewChat, setIsDraftNewChat] = useState(false)

  // Slash command autocomplete state
  const [slashMenuOpen, setSlashMenuOpen] = useState(false)
  const [slashActiveIndex, setSlashActiveIndex] = useState(0)
  const [slashMatches, setSlashMatches] = useState<SlashCommand[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  // Session-scoped streaming state keyed by session id (or 'draft' for new sessions)
  const [streamingStateMap, setStreamingStateMap] = useState<Record<string, SessionStreamingState>>({})
  const [thinkingSessionKey, setThinkingSessionKey] = useState<SessionKey | null>(null)
  const optIdCounter = useRef(0)
  const streamingTextRef = useRef('')
  const chatEndRef = useRef<HTMLDivElement>(null)
  const scrollFrameRef = useRef<number | null>(null)
  const previousScrollStateRef = useRef<{ sessionId: number | null; messageCount: number }>({ sessionId: null, messageCount: 0 })

  // Resolve the effective session key for the currently active session
  const currentSessionKey: SessionKey = activeSessionId ?? 'draft'
  const currentStreaming = streamingStateMap[currentSessionKey] ?? emptyStreamingState()
  const optimisticMessages = currentStreaming.optimisticMessages
  const streamingText = currentStreaming.streamingText
  const streamingToolCalls = currentStreaming.streamingToolCalls
  const isThinking = thinkingSessionKey === currentSessionKey

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
  const scrollMessageCount = displayMessages.length
  const scrollTargetKey = `${activeSessionId ?? 'draft'}:${scrollMessageCount}:${streamingText.length}:${streamingToolCalls.length}:${isLoadingSession ? 'loading' : 'ready'}`

  // Right panel visible when sessions exist
  const showRightPanel = sessions.length > 0

  // Reset on workspace change
  useEffect(() => {
    if (activeSession && activeSession.workspaceId !== workspaceId) {
      setActiveSessionId(null)
      setIsDraftNewChat(false)
      setStreamingStateMap({})
      setThinkingSessionKey(null)
      streamingTextRef.current = ''
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

  // ---------------------------------------------------------------------------
  // Slash command autocomplete helpers
  // ---------------------------------------------------------------------------

  const updateSlashMenu = useCallback((value: string) => {
    const matches = filterCommands(value)
    setSlashMatches(matches)
    setSlashMenuOpen(matches.length > 0)
    setSlashActiveIndex(0)
  }, [])

  const closeSlashMenu = useCallback(() => {
    setSlashMenuOpen(false)
    setSlashMatches([])
    setSlashActiveIndex(0)
  }, [])

  const handleSlashSelect = useCallback(
    (cmd: SlashCommand) => {
      setInput(cmd.command)
      closeSlashMenu()
      inputRef.current?.focus()
    },
    [closeSlashMenu],
  )

  const handleInputChange = useCallback(
    (value: string) => {
      setInput(value)
      updateSlashMenu(value)
    },
    [updateSlashMenu],
  )

  const handleInputKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (!slashMenuOpen || slashMatches.length === 0) return

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setSlashActiveIndex((prev) => (prev + 1) % slashMatches.length)
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        setSlashActiveIndex((prev) => (prev - 1 + slashMatches.length) % slashMatches.length)
      } else if (event.key === 'Enter') {
        event.preventDefault()
        handleSlashSelect(slashMatches[slashActiveIndex])
      } else if (event.key === 'Escape') {
        event.preventDefault()
        closeSlashMenu()
      }
    },
    [slashMenuOpen, slashMatches, slashActiveIndex, handleSlashSelect, closeSlashMenu],
  )

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      const value = input.trim()
      if (!value || !workspaceId) return

      // Determine which session key this submission targets
      const submitKey: SessionKey = activeSessionId ?? 'draft'
      if (thinkingSessionKey === submitKey) return // already streaming for this session

      const userOptId = `opt-user-${++optIdCounter.current}` as const

      // Local helper scoped to this invocation to avoid dependency issues
      const patch = (key: SessionKey, updater: (prev: SessionStreamingState) => SessionStreamingState) => {
        setStreamingStateMap((map) => ({ ...map, [key]: updater(map[key] ?? emptyStreamingState()) }))
      }

      // Optimistically render user message only; streaming text serves as the assistant placeholder
      patch(submitKey, (prev) => ({
        ...prev,
        optimisticMessages: [...prev.optimisticMessages, { __optimistic: true, id: userOptId, role: 'user', content: value }],
        streamingText: '',
        streamingToolCalls: [],
      }))
      streamingTextRef.current = ''
      setThinkingSessionKey(submitKey)
      setInput('')
      closeSlashMenu()

      // Track the resolved key; updated by onMetadata once the server assigns a session id
      let resolvedKey: SessionKey = submitKey

      await sendMessage(
        {
          workspaceId,
          sessionId: activeSessionId,
          message: value,
        },
        {
          onMetadata: (event) => {
            const newKey: SessionKey = event.session_id
            // Migrate 'draft' bucket to the real session id if needed
            if (submitKey === 'draft') {
              setStreamingStateMap((map) => {
                const draft = map['draft'] ?? emptyStreamingState()
                const { draft: _, ...rest } = map
                void _
                return { ...rest, [newKey]: draft }
              })
            }
            resolvedKey = newKey
            setActiveSessionId(event.session_id)
            setThinkingSessionKey(newKey)
            setIsDraftNewChat(false)
          },
          onTextDelta: (event) => {
            streamingTextRef.current += event.delta
            patch(resolvedKey, (prev) => ({
              ...prev,
              streamingText: streamingTextRef.current,
            }))
          },
          onToolCall: (event) => {
            const callId = event.call_id || `${event.tool_name}-${Date.now()}`
            patch(resolvedKey, (prev) => ({
              ...prev,
              streamingToolCalls: [...prev.streamingToolCalls, { callId, toolName: event.tool_name, status: 'running' }],
            }))
          },
          onToolResult: (event) => {
            if (!event.call_id) return
            patch(resolvedKey, (prev) => ({
              ...prev,
              streamingToolCalls: prev.streamingToolCalls.map((tool) =>
                tool.callId === event.call_id ? { ...tool, status: event.ok ? 'done' : 'failed' } : tool,
              ),
            }))
          },
          onDecisionBrief: () => {
            patch(resolvedKey, (prev) => ({
              ...prev,
              streamingText: '',
              streamingToolCalls: [],
            }))
            streamingTextRef.current = ''
          },
          onCommandResult: () => {
            patch(resolvedKey, (prev) => ({
              ...prev,
              streamingText: '',
              streamingToolCalls: [],
            }))
            streamingTextRef.current = ''
          },
          onDone: () => {
            const finalStreamedText = streamingTextRef.current
            patch(resolvedKey, (prev) => {
              const newOpts: DisplayMessage[] = finalStreamedText.trim()
                ? [
                    ...prev.optimisticMessages,
                    { __optimistic: true as const, id: `opt-assistant-${++optIdCounter.current}`, role: 'assistant' as const, content: finalStreamedText },
                  ]
                : prev.optimisticMessages
              return { ...prev, streamingText: '', streamingToolCalls: [], optimisticMessages: newOpts }
            })
            streamingTextRef.current = ''
            setThinkingSessionKey(null)
          },
          onError: (event) => {
            console.error('Stream error:', event.error)
            const finalStreamedText = streamingTextRef.current
            patch(resolvedKey, (prev) => {
              const newOpts: DisplayMessage[] = finalStreamedText.trim()
                ? [
                    ...prev.optimisticMessages,
                    { __optimistic: true as const, id: `opt-assistant-${++optIdCounter.current}`, role: 'assistant' as const, content: finalStreamedText },
                  ]
                : prev.optimisticMessages
              return { ...prev, streamingText: '', streamingToolCalls: [], optimisticMessages: newOpts }
            })
            streamingTextRef.current = ''
            setThinkingSessionKey(null)
            setInput((current) => (current.trim() ? current : value))
          },
        },
      )
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [input, thinkingSessionKey, workspaceId, activeSessionId, sendMessage, closeSlashMenu],
  )

  function handleNewChat() {
    abort()
    setThinkingSessionKey(null)
    setActiveSessionId(null)
    setIsDraftNewChat(true)
    setInput('')
    streamingTextRef.current = ''
    // Clear only draft streaming state, not persisted sessions
    setStreamingStateMap((prev) => {
      const { draft: _, ...rest } = prev
      void _
      return rest
    })
    closeSlashMenu()
  }

  function handleStop() {
    abort()
    setThinkingSessionKey(null)
  }

  return (
    <main className="flex h-full min-h-0 flex-col overflow-hidden bg-card text-foreground">
      <div
        className={`grid h-full min-h-0 overflow-hidden ${showRightPanel ? 'grid-cols-[minmax(0,1fr)_clamp(18rem,22vw,23rem)]' : 'grid-cols-1'}`}
      >
        <section
          className={showRightPanel ? 'flex min-h-0 min-w-0 flex-col border-r border-border/70' : 'flex min-h-0 min-w-0 flex-col'}
        >
          <header className="shrink-0 px-8 pt-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.3em] text-text-hint">
                {activeSession ? `Session started: ${formatDate(activeSession.createdAt)}` : 'Start a Workspace-scoped Chat Session'}
              </p>

              {activeWorkspace && (
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={handleNewChat}
                    disabled={!activeWorkspace || isStreaming}
                    className="inline-flex items-center gap-1.5 rounded-full border border-border/70 px-4 py-2 text-xs font-semibold text-foreground transition hover:border-primary/30 hover:bg-surface-subtle hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    New Chat
                  </button>
                </div>
              )}
            </div>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto px-8 py-8 scroll-smooth">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
              {!activeWorkspace ? (
                <EmptyChatState
                  title="Select a Workspace"
                  description="Choose or create a Workspace from the bottom-left switcher before starting Chat."
                />
              ) : sessionsError ? (
                <EmptyChatState title="Could not load Chat" description="Check that the API is running, then try again." />
              ) : isLoadingSessions || (isLoadingSession && displayMessages.length === 0) ? (
                <EmptyChatState title="Loading Chat" description="Fetching persisted Chat Sessions and messages." />
              ) : displayMessages.length === 0 ? (
                <EmptyChatState title="Ask a strategic question" description="Messages will be persisted to this Workspace-scoped Chat Session." />
              ) : (
                displayMessages.map((message) => (
                  <div key={message.id} id={`message-${message.id}`}>
                    {message.role === 'user' ? (
                      <UserBubble content={message.content} />
                    ) : !isOptimistic(message) && message.messageType === 'decision_brief' && message.decisionBriefId && workspaceId ? (
                      <DecisionBriefCard briefId={message.decisionBriefId} workspaceId={workspaceId} />
                    ) : !isOptimistic(message) && message.messageType === 'command_result' ? (
                      <CommandResultMessage content={message.content} />
                    ) : (
                      <AssistantMessage
                        message={message}
                        citations={
                          !isOptimistic(message) ? (activeSession?.citations.filter((citation) => citation.messageId === message.id) ?? []) : []
                        }
                        toolCalls={
                          !isOptimistic(message) ? (activeSession?.toolCalls.filter((toolCall) => toolCall.messageId === message.id) ?? []) : []
                        }
                        streamingToolCalls={isOptimistic(message) ? streamingToolCalls : []}
                        showThinking={isOptimistic(message) && isThinking && !streamingText}
                      />
                    )}
                  </div>
                ))
              )}
              <div ref={chatEndRef} aria-hidden="true" />
            </div>
          </div>

          <footer className="shrink-0 px-8 py-5 pt-0">
            <div className="mx-auto max-w-4xl">
              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="relative rounded-[20px] border border-border/70 bg-white px-4 py-3 shadow-[0_8px_28px_rgba(15,23,42,0.05)] transition focus-within:border-primary/30 focus-within:shadow-[0_12px_36px_rgba(79,70,229,0.08)]">
                  {slashMenuOpen && (
                    <SlashCommandMenu
                      commands={slashMatches}
                      activeIndex={slashActiveIndex}
                      onSelect={handleSlashSelect}
                      onClose={closeSlashMenu}
                    />
                  )}
                  <div className="flex items-center gap-3">
                    <input
                      ref={inputRef}
                      value={input}
                      onChange={(event) => handleInputChange(event.target.value)}
                      onKeyDown={handleInputKeyDown}
                      placeholder="Ask a strategic question or type '/'"
                      role="combobox"
                      aria-expanded={slashMenuOpen}
                      aria-controls={slashMenuOpen ? 'slash-command-menu' : undefined}
                      aria-autocomplete="list"
                      className="min-w-0 flex-1 border-0 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
                    />
                    {isStreaming || isThinking ? (
                      <button
                        type="button"
                        onClick={handleStop}
                        className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-foreground text-card transition duration-200 hover:-translate-y-0.5 hover:bg-foreground/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                        aria-label="Stop response"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    ) : (
                      <button
                        type="submit"
                        disabled={!input.trim() || !activeWorkspace}
                        className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground transition duration-200 hover:-translate-y-0.5 hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
                        aria-label="Send message"
                      >
                        <Send className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-text-hint">
                  <CommandChip command="/decision-brief" label="Generate Brief" onClick={() => setInput('/decision-brief')} />
                  <span className="ml-auto">Copilot can make mistakes. Consider verifying.</span>
                </div>
              </form>
            </div>
          </footer>
        </section>

        {showRightPanel && (
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
    </main>
  )
}
