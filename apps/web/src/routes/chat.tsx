import { createFileRoute } from '@tanstack/react-router'
import { Bot, ChevronRight, Eye, FileSpreadsheet, FileText, Lightbulb, Mic, Paperclip, Send, Workflow, X } from 'lucide-react'
import { type FormEvent, type ReactNode, useCallback, useEffect, useRef, useState } from 'react'
import { useChatSession, useChatSessions, useStreamChat } from '../features/chat/hooks'
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
  const { sendMessage } = useStreamChat()

  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [optimisticMessages, setOptimisticMessages] = useState<DisplayMessage[]>([])
  const [streamingText, setStreamingText] = useState('')
  const optIdCounter = useRef(0)

  const persistedMessages: ChatMessage[] = activeSession?.messages ?? []

  // Compose displayed messages: persisted + any optimistic that aren't replaced yet
  const messages: DisplayMessage[] = [
    ...persistedMessages,
    ...optimisticMessages.filter((om) => !isOptimistic(om) || !persistedMessages.some((pm) => pm.content === om.content && pm.role === om.role)),
  ]

  // If we have streaming text, append a streaming assistant message
  const streamingMessage: OptimisticAssistantMessage | null = streamingText
    ? { __optimistic: true, id: `opt-stream-${Date.now()}`, role: 'assistant', content: streamingText }
    : null
  const displayMessages: DisplayMessage[] = streamingMessage ? [...messages, streamingMessage] : messages

  // Reset on workspace change
  useEffect(() => {
    if (activeSession?.workspaceId !== workspaceId) {
      setActiveSessionId(null)
    }
  }, [activeSession?.workspaceId, workspaceId])

  // Auto-select first session
  useEffect(() => {
    if (activeSessionId === null && sessions.length > 0) {
      setActiveSessionId(sessions[0].id)
    }
  }, [activeSessionId, sessions])

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      const value = input.trim()
      if (!value || isThinking || !workspaceId) return

      const userOptId = `opt-user-${++optIdCounter.current}` as const
      const assistantOptId = `opt-assistant-${++optIdCounter.current}` as const

      // Optimistically render user message + empty assistant placeholder
      setOptimisticMessages((prev) => [
        ...prev,
        { __optimistic: true, id: userOptId, role: 'user', content: value },
        { __optimistic: true, id: assistantOptId, role: 'assistant', content: '' },
      ])
      setStreamingText('')
      setIsThinking(true)
      setInput('')

      await sendMessage(
        {
          workspaceId,
          sessionId: activeSessionId,
          message: value,
        },
        {
          onSessionCreated: (event) => {
            setActiveSessionId(event.session.id)
          },
          onUserMessageSaved: () => {
            // Backend persisted user message; optimistic one will be hidden once session refetches
          },
          onAssistantStarted: () => {
            // Assistant placeholder already shown
          },
          onTextDelta: (event) => {
            setStreamingText((prev) => prev + event.delta)
          },
          onAssistantCompleted: () => {
            // Refetch happens inside useStreamChat; clear optimistic state
            setStreamingText('')
            setOptimisticMessages([])
            setIsThinking(false)
          },
          onError: (event) => {
            console.error('Stream error:', event.error)
            setStreamingText('')
            setOptimisticMessages([])
            setIsThinking(false)
            // Restore input so user can retry
            setInput(value)
          },
        },
      )
    },
    [input, isThinking, workspaceId, activeSessionId, sendMessage],
  )

  function handleNewChat() {
    // New Chat = local draft only: clear active session, no backend POST
    setActiveSessionId(null)
    setOptimisticMessages([])
    setStreamingText('')
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_376px] overflow-hidden text-foreground">
      <section className="flex min-h-0 min-w-0 flex-col border-r border-border">
        <div className="min-h-0 flex-1 overflow-y-auto px-10 py-8">
          <div className="mb-7 flex items-center justify-center gap-4">
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-text-hint">
              {activeSession ? `Session started: ${formatDate(activeSession.createdAt)}` : 'Start a Workspace-scoped Chat Session'}
            </p>
            {activeWorkspace && (
              <button
                type="button"
                onClick={handleNewChat}
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-surface-subtle"
              >
                New Chat
              </button>
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
              displayMessages.map((message) =>
                message.role === 'user' ? (
                  <UserBubble key={message.id} content={message.content} />
                ) : (
                  <AssistantCard
                    key={message.id}
                    message={message}
                    citations={!isOptimistic(message) ? (activeSession?.citations.filter((citation) => citation.messageId === message.id) ?? []) : []}
                    toolCalls={!isOptimistic(message) ? (activeSession?.toolCalls.filter((toolCall) => toolCall.messageId === message.id) ?? []) : []}
                  />
                ),
              )
            )}

            {isThinking && !streamingText && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-accent text-primary">
                  <Bot className="h-4 w-4" />
                </div>
                Intelligence Copilot is synthesizing Sources...
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="shrink-0 border-t border-border bg-card px-8 py-5">
          <div className="mx-auto max-w-[850px]">
            <div className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3 shadow-sm">
              <button type="button" className="text-text-hint hover:text-primary" aria-label="Attach Source">
                <Paperclip className="h-5 w-5" />
              </button>
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask a strategic question or type '/'"
                className="min-w-0 flex-1 border-0 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
              <button type="button" className="text-text-hint hover:text-primary" aria-label="Voice input">
                <Mic className="h-5 w-5" />
              </button>
              <button
                type="submit"
                disabled={!input.trim() || isThinking || !activeWorkspace}
                className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-3 flex items-center gap-3 text-xs text-text-hint">
              <CommandChip command="/decision-brief" label="Generate Brief" />
              <span className="ml-auto">Copilot can make mistakes. Consider verifying.</span>
            </div>
          </div>
        </form>
      </section>

      <SourcesPanel
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        citations={activeSession?.citations ?? []}
        toolCalls={activeSession?.toolCalls ?? []}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[65%] rounded-[16px_16px_4px_16px] bg-user-bubble px-5 py-4 text-sm leading-7 text-foreground shadow-sm">{content}</div>
    </div>
  )
}

function AssistantCard({
  message,
  citations,
  toolCalls,
}: {
  message: DisplayMessage
  citations: MessageSourceCitation[]
  toolCalls: AgentToolCall[]
}) {
  return (
    <article>
      <div className="mb-5 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-accent text-primary">
          <Bot className="h-5 w-5" />
        </div>
        <h2 className="font-heading text-lg font-semibold text-foreground">Intelligence Copilot</h2>
      </div>

      <div className="rounded-2xl border border-border bg-card p-8 shadow-sm">
        <div className="border-l-4 border-highlight pl-7">
          <p className="whitespace-pre-line text-sm leading-7 text-foreground">{message.content}</p>

          {/* Only show evidence / action sections when content is non-empty (i.e. not the streaming placeholder) */}
          {message.content.length > 0 && !isOptimistic(message) && (
            <>
              <div className="mt-7 rounded-xl border border-border bg-surface-subtle p-5">
                <div className="mb-4 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  Cited Evidence
                </div>
                {citations.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No persisted citations for this response.</p>
                ) : (
                  <div className="flex flex-wrap gap-3">
                    {citations.map((citation) => (
                      <EvidenceChip key={citation.id} citation={citation} />
                    ))}
                  </div>
                )}
              </div>

              {toolCalls.length > 0 && (
                <div className="mt-7 rounded-xl border border-border bg-card p-5">
                  <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                    <Workflow className="h-4 w-4" />
                    Tools Used
                  </div>
                  <div className="space-y-2">
                    {toolCalls.map((toolCall) => (
                      <p key={toolCall.id} className="text-sm text-muted-foreground">
                        <span className="font-mono text-xs uppercase tracking-[0.12em] text-text-hint">{toolCall.status}</span> {toolCall.toolName}:{' '}
                        {toolCall.summary}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-7 rounded-xl border border-highlight-soft bg-accent p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-primary">
                  <Lightbulb className="h-4 w-4" />
                  Recommended Action
                </div>
                <p className="text-sm leading-6 text-foreground">
                  Continue the discussion here; this Chat Session remains scoped to its original Workspace.
                </p>
              </div>

              <div className="mt-7 grid grid-cols-3 gap-3">
                <ActionButton icon={<Eye className="h-4 w-4" />} label="View Sources" />
                <ActionButton icon={<Workflow className="h-4 w-4" />} label="View Trace" />
                <button
                  type="button"
                  className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
                >
                  <FileText className="h-4 w-4" />
                  Generate Decision Brief
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </article>
  )
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

function ActionButton({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <button
      type="button"
      className="flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-3 text-sm font-semibold text-foreground shadow-sm hover:bg-surface-subtle"
    >
      {icon}
      {label}
    </button>
  )
}

function CommandChip({ command, label }: { command: string; label: string }) {
  return (
    <span>
      <span className="rounded bg-chip-gray px-2 py-1 font-mono text-text-hint">{command}</span> {label}
    </span>
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
  if (citations.length === 0 && toolCalls.length === 0) {
    return (
      <SourceCard
        type="csv"
        name="No citations yet"
        badge="Sources"
        quote="Ask a source-grounded question after uploading ready Sources. Citations will appear here."
      />
    )
  }

  const uploadedCitations = citations.filter((c) => c.citationType === 'uploaded_source')
  const webCitations = citations.filter((c) => c.citationType === 'web')

  return (
    <div className="space-y-4">
      {uploadedCitations.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Uploaded Sources</p>
          <div className="space-y-3">
            {uploadedCitations.map((citation) => (
              <SourceCard
                key={citation.id}
                type={citation.title?.toLowerCase().endsWith('.pdf') ? 'pdf' : 'csv'}
                name={citation.title || `Source #${citation.sourceId ?? 'unknown'}`}
                badge={citation.citationStatus === 'available' ? 'Uploaded Source' : citation.citationStatus}
                quote={citation.quote || 'Citation available without quote.'}
                pageNumber={citation.pageNumber}
                citationStatus={citation.citationStatus}
              />
            ))}
          </div>
        </div>
      )}

      {webCitations.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Web Sources</p>
          <div className="space-y-3">
            {webCitations.map((citation) => (
              <SourceCard
                key={citation.id}
                type="web"
                name={citation.title || citation.domain || 'Web Source'}
                badge="Web Source"
                quote={citation.quote || citation.url || 'Web citation without quote.'}
                url={citation.url}
                domain={citation.domain}
                citationStatus={citation.citationStatus}
              />
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
function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function SourceCard({
  type,
  name,
  badge,
  quote,
  pageNumber,
  url,
  domain,
  citationStatus,
}: {
  type: 'pdf' | 'csv' | 'web'
  name: string
  badge: string
  quote: string
  pageNumber?: number | null
  url?: string | null
  domain?: string | null
  citationStatus?: string | null
}) {
  const Icon = type === 'pdf' ? FileText : type === 'web' ? Eye : FileSpreadsheet
  const color = type === 'pdf' ? 'text-status-failed-foreground' : type === 'web' ? 'text-primary' : 'text-status-ready-foreground'
  const isWarning = citationStatus && citationStatus !== 'available'
  return (
    <article className={`rounded-xl border bg-card p-5 shadow-sm ${isWarning ? 'border-status-failed-foreground/40' : 'border-border'}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className={`h-4 w-4 shrink-0 ${color}`} />
          <h3 className="truncate text-sm font-semibold text-foreground">{name}</h3>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isWarning && (
            <span className="rounded bg-status-failed-foreground/10 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-status-failed-foreground">
              {citationStatus}
            </span>
          )}
          <span className="rounded bg-chip-gray px-2 py-1 font-mono text-[11px] text-text-hint">{badge}</span>
        </div>
      </div>
      <blockquote className="border-l-2 border-border pl-4 text-sm italic leading-6 text-muted-foreground">"{quote}"</blockquote>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-text-hint">
        {pageNumber != null && <span className="font-mono">p.{pageNumber}</span>}
        {domain && <span className="font-mono">{domain}</span>}
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="truncate font-mono text-primary hover:underline">
            {url}
          </a>
        )}
      </div>
    </article>
  )
}

function PanelLink({ label }: { label: string }) {
  return (
    <button className="flex w-full items-center justify-between py-3 text-sm font-medium text-foreground hover:text-primary" type="button">
      {label}
      <ChevronRight className="h-4 w-4" />
    </button>
  )
}
