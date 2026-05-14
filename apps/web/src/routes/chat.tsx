import { createFileRoute } from '@tanstack/react-router'
import { Bot, ChevronRight, ExternalLink, Eye, FileSpreadsheet, FileText, Mic, Paperclip, Send, Workflow, X } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { useChatSession, useChatSessions, useCreateChatSession, useStreamChat } from '../features/chat/hooks'
import { DecisionBriefCard } from '../features/decision-briefs/components/DecisionBriefCard'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { AgentToolCall, ChatMessage, MessageSourceCitation } from '../types/chat'

export const Route = createFileRoute('/chat')({
  component: ChatPage,
})

// ---------------------------------------------------------------------------
// Optimistic message types (local-only, never persisted as-is)
// ---------------------------------------------------------------------------

type OptimisticUserMessage = {
  __optimistic: true
  id: string
  role: 'user'
  content: string
}

type OptimisticAssistantMessage = {
  __optimistic: true
  id: string
  role: 'assistant'
  content: string
}

type StreamingToolCall = {
  callId: string
  toolName: string
  status: 'running' | 'done' | 'failed'
}

type DisplayMessage = ChatMessage | OptimisticUserMessage | OptimisticAssistantMessage

function isOptimistic(msg: DisplayMessage): msg is OptimisticUserMessage | OptimisticAssistantMessage {
  return '__optimistic' in msg && msg.__optimistic === true
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

  const persistedMessages: ChatMessage[] = (activeSession?.messages ?? []).filter((message) => !(isThinking && message.role === 'assistant' && message.status === 'streaming'))

  // Compose displayed messages: persisted + any optimistic that aren't replaced yet
  const messages: DisplayMessage[] = [
    ...persistedMessages,
    ...optimisticMessages.filter((om) => !isOptimistic(om) || !persistedMessages.some((pm) => pm.content === om.content && pm.role === om.role)),
  ]

  // If we have streaming text, append a streaming assistant message
  const streamingMessage: OptimisticAssistantMessage | null = isThinking
    ? { __optimistic: true, id: 'opt-streaming-assistant', role: 'assistant', content: streamingText }
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
            setStreamingToolCalls((prev) => prev.map((tool) => (tool.callId === event.call_id ? { ...tool, status: event.ok ? 'done' : 'failed' } : tool)))
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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300">
      <div className="max-w-[65%] rounded-[16px_16px_4px_16px] bg-user-bubble px-5 py-4 text-sm leading-7 text-foreground shadow-sm">{content}</div>
    </div>
  )
}

function AssistantMessage({
  message,
  citations,
  toolCalls,
  streamingToolCalls,
  showThinking,
}: {
  message: DisplayMessage
  citations: MessageSourceCitation[]
  toolCalls: AgentToolCall[]
  streamingToolCalls: StreamingToolCall[]
  showThinking: boolean
}) {
  const processItems = [
    ...streamingToolCalls.map((tool) => ({ id: tool.callId, label: processLabelForTool(tool.toolName), status: tool.status })),
    ...toolCalls.map((toolCall) => ({
      id: String(toolCall.id),
      label: processLabelForTool(toolCall.toolName),
      status: toolCall.status === 'failed' ? 'failed' : toolCall.status === 'running' ? 'running' : 'done',
    })),
  ]

  return (
    <article className="space-y-3 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-hint">
        <Bot className="h-4 w-4 text-primary" />
        Intelligence Copilot
      </div>

      {(showThinking || processItems.length > 0) && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {showThinking && processItems.length === 0 && <ProcessPill label="Thinking…" status="running" />}
          {processItems.map((item) => (
            <ProcessPill key={item.id} label={item.label} status={item.status} />
          ))}
        </div>
      )}

      {message.content && <p className="whitespace-pre-line text-[15px] leading-8 text-foreground">{message.content}</p>}

      {message.content.length > 0 && citations.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {citations.map((citation) => (
            <EvidenceChip key={citation.id} citation={citation} />
          ))}
        </div>
      )}

      <TraceLink message={message} />
    </article>
  )
}

function TraceLink({ message }: { message: DisplayMessage }) {
  if (isOptimistic(message)) return null
  const url = message.traceUrl
  if (!url) return null
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-xs text-text-hint hover:text-primary transition-colors"
      title="Open trace in Langfuse"
    >
      <ExternalLink className="h-3.5 w-3.5" />
      View trace
    </a>
  )
}

function ProcessPill({ label, status }: { label: string; status: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-subtle px-3 py-1 font-mono text-[11px] text-text-hint">
      <Workflow className="h-3.5 w-3.5" />
      {label}
      <span className={status === 'failed' ? 'text-status-failed-foreground' : status === 'done' ? 'text-status-ready-foreground' : 'text-text-hint'}>
        {status === 'running' ? 'running' : status}
      </span>
    </span>
  )
}

function processLabelForTool(toolName: string) {
  if (toolName === 'retrieve_company_knowledge') return 'Searching company Sources…'
  if (toolName === 'tavily_web_search') return 'Searching web…'
  return 'Using tool…'
}

function EvidenceChip({ citation }: { citation: MessageSourceCitation }) {
  const isWeb = citation.citationType === 'web'
  const Icon = isWeb ? Eye : citation.title?.toLowerCase().endsWith('.pdf') ? FileText : FileSpreadsheet
  const color = isWeb ? 'text-primary' : 'text-status-ready-foreground'
  const label = isWeb ? citation.domain || citation.title || 'Web Source' : citation.title || `Source #${citation.sourceId ?? 'unknown'}`
  return (
    <span
      className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 font-mono text-xs text-foreground shadow-sm"
      title={citation.quote ?? citation.url ?? undefined}
    >
      <Icon className={`h-4 w-4 ${color}`} />[{citation.ordinal ?? citation.id}] {label}
      {citation.citationStatus !== 'available' && <span className="text-status-failed-foreground">warning</span>}
    </span>
  )
}

function CommandChip({ command, label, onClick }: { command: string; label: string; onClick?: () => void }) {
  const content = (
    <>
      <span className="rounded bg-chip-gray px-2 py-1 font-mono text-text-hint">{command}</span> {label}
    </>
  )
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className="inline-flex items-center gap-1 transition hover:text-foreground">
        {content}
      </button>
    )
  }
  return <span>{content}</span>
}

function CommandResultMessage({ content }: { content: string }) {
  return (
    <article className="rounded-2xl border border-dashed border-border bg-surface-subtle p-5 text-sm leading-7 text-foreground whitespace-pre-line">
      {content}
    </article>
  )
}

function EmptyChatState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-muted bg-surface-subtle p-8 text-center">
      <h2 className="font-heading text-lg font-semibold text-foreground">{title}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

function SourcesPanel({
  sessions,
  activeSessionId,
  onSelectSession,
  citations,
  toolCalls,
}: {
  sessions: { id: number; title: string; updatedAt: string }[]
  activeSessionId: number | null
  onSelectSession: (id: number) => void
  citations: MessageSourceCitation[]
  toolCalls: AgentToolCall[]
}) {
  return (
    <aside className="flex min-h-0 flex-col bg-surface-subtle">
      <div className="flex items-center justify-between border-b border-border bg-card px-6 py-6">
        <h2 className="font-heading text-xl font-semibold text-foreground">Sources Used</h2>
        <button className="text-text-hint hover:text-foreground" type="button" aria-label="Close sources panel">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 space-y-5 overflow-auto p-6">
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Recent Sessions</p>
          <div className="space-y-2">
            {sessions.length === 0 ? (
              <p className="rounded-xl border border-dashed border-muted bg-card p-4 text-sm text-muted-foreground">
                No persisted Chat Sessions yet.
              </p>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => onSelectSession(session.id)}
                  className={`w-full rounded-xl border px-4 py-3 text-left text-sm shadow-sm transition hover:bg-surface-subtle ${
                    activeSessionId === session.id ? 'border-highlight bg-accent text-foreground' : 'border-border bg-card text-muted-foreground'
                  }`}
                >
                  <span className="block truncate font-semibold text-foreground">{session.title}</span>
                  <span className="mt-1 block font-mono text-[11px] uppercase tracking-[0.12em] text-text-hint">{formatDate(session.updatedAt)}</span>
                </button>
              ))
            )}
          </div>
        </div>
        <SessionSources citations={citations} toolCalls={toolCalls} />
      </div>

      <div className="border-t border-border bg-card px-6 py-5">
        <PanelLink label="Trace Reference" />
        <PanelLink label="Drafted Briefs" />
      </div>
    </aside>
  )
}

function SessionSources({ citations, toolCalls }: { citations: MessageSourceCitation[]; toolCalls: AgentToolCall[] }) {
  const uploadedCitations = citations.filter((c) => c.citationType === 'uploaded_source')
  const webCitations = citations.filter((c) => c.citationType === 'web')
  const uploadedGroups = groupCitations(uploadedCitations)
  const webGroups = groupCitations(webCitations)

  return (
    <div className="space-y-4">
      {uploadedCitations.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Uploaded Sources</p>
          <div className="space-y-3">
            {uploadedGroups.map((group) => (
              <SourceGroupCard key={group.key} group={group} type={group.title.toLowerCase().endsWith('.pdf') ? 'pdf' : 'csv'} />
            ))}
          </div>
        </div>
      )}

      {webCitations.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Web Sources</p>
          <div className="space-y-3">
            {webGroups.map((group) => (
              <SourceGroupCard key={group.key} group={group} type="web" />
            ))}
          </div>
        </div>
      )}

      {toolCalls.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Tool Calls</p>
          <div className="space-y-2">
            {toolCalls.map((tc) => (
              <div key={tc.id} className="rounded-lg border border-border bg-card px-4 py-3 text-xs text-muted-foreground shadow-sm">
                <span className="font-mono uppercase tracking-[0.12em] text-text-hint">{tc.status}</span>{' '}
                <span className="font-semibold text-foreground">{tc.toolName}</span>
                {tc.summary && <span className="ml-1">— {tc.summary}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

type CitationGroup = {
  key: string
  title: string
  badge: string
  citations: MessageSourceCitation[]
}

function groupCitations(citations: MessageSourceCitation[]): CitationGroup[] {
  const groups = new Map<string, CitationGroup>()
  for (const citation of citations) {
    const key = citation.citationType === 'web' ? citation.url || citation.domain || citation.title || `web-${citation.id}` : String(citation.sourceId ?? citation.title ?? citation.id)
    const title = citation.citationType === 'web' ? citation.title || citation.domain || 'Web Source' : citation.title || `Source #${citation.sourceId ?? 'unknown'}`
    const badge = citation.citationType === 'web' ? 'Web Source' : citation.citationStatus === 'available' ? 'Uploaded Source' : citation.citationStatus
    const group = groups.get(key)
    if (group) {
      group.citations.push(citation)
    } else {
      groups.set(key, { key, title, badge, citations: [citation] })
    }
  }
  return Array.from(groups.values())
}

function SourceGroupCard({ group, type }: { group: CitationGroup; type: 'pdf' | 'csv' | 'web' }) {
  const firstCitation = group.citations[0]
  const Icon = type === 'pdf' ? FileText : type === 'web' ? Eye : FileSpreadsheet
  const color = type === 'pdf' ? 'text-status-failed-foreground' : type === 'web' ? 'text-primary' : 'text-status-ready-foreground'
  const hasWarning = group.citations.some((citation) => citation.citationStatus !== 'available')

  return (
    <details className={`rounded-xl border bg-card p-5 shadow-sm ${hasWarning ? 'border-status-failed-foreground/40' : 'border-border'}`}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className={`h-4 w-4 shrink-0 ${color}`} />
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-foreground">{group.title}</h3>
            <p className="mt-1 font-mono text-[11px] text-text-hint">{group.citations.length} citation{group.citations.length > 1 ? 's' : ''}</p>
          </div>
        </div>
        <span className="rounded bg-chip-gray px-2 py-1 font-mono text-[11px] text-text-hint">{group.badge}</span>
      </summary>
      <div className="mt-4 space-y-3">
        {group.citations.map((citation) => (
          <blockquote key={citation.id} className="border-l-2 border-border pl-4 text-sm italic leading-6 text-muted-foreground">
            “{citation.quote || citation.snippet || citation.url || 'Citation available without quote.'}”
            <span className="mt-2 block text-xs not-italic text-text-hint">
              [{citation.ordinal ?? citation.id}]
              {citation.pageNumber != null ? ` p.${citation.pageNumber}` : ''}
              {citation.domain ? ` · ${citation.domain}` : ''}
            </span>
          </blockquote>
        ))}
        {firstCitation?.url && (
          <a href={firstCitation.url} target="_blank" rel="noopener noreferrer" className="block truncate font-mono text-xs text-primary hover:underline">
            {firstCitation.url}
          </a>
        )}
      </div>
    </details>
  )
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function PanelLink({ label }: { label: string }) {
  return (
    <button className="flex w-full items-center justify-between py-3 text-sm font-medium text-foreground hover:text-primary" type="button">
      {label}
      <ChevronRight className="h-4 w-4" />
    </button>
  )
}
