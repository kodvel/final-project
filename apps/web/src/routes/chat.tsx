import { createFileRoute } from '@tanstack/react-router'
import { Bot, ChevronRight, Eye, FileSpreadsheet, FileText, Lightbulb, Mic, Paperclip, Send, Workflow, X } from 'lucide-react'
import { type FormEvent, type ReactNode, useEffect, useState } from 'react'
import { useChatSession, useChatSessions, useCreateChatSession, useSendChatMessage } from '../features/chat/hooks'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { ChatMessage } from '../types/chat'

export const Route = createFileRoute('/chat')({
  component: ChatPage,
})

export function ChatPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? null
  const { data: sessions = [], isLoading: isLoadingSessions, error: sessionsError } = useChatSessions(workspaceId)
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const { data: activeSession, isLoading: isLoadingSession } = useChatSession(activeSessionId, workspaceId)
  const createSession = useCreateChatSession()
  const sendMessage = useSendChatMessage()
  const [input, setInput] = useState('')
  const isThinking = createSession.isPending || sendMessage.isPending
  const messages = activeSession?.messages ?? []

  useEffect(() => {
    if (activeSession?.workspaceId !== workspaceId) {
      setActiveSessionId(null)
    }
  }, [activeSession?.workspaceId, workspaceId])

  useEffect(() => {
    if (activeSessionId === null && sessions.length > 0) {
      setActiveSessionId(sessions[0].id)
    }
  }, [activeSessionId, sessions])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const value = input.trim()
    if (!value || isThinking || !activeWorkspace) return

    try {
      const sessionId = activeSessionId ?? (await createSession.mutateAsync({ workspaceId: activeWorkspace.id })).id
      setActiveSessionId(sessionId)
      await sendMessage.mutateAsync({ sessionId, workspaceId: activeWorkspace.id, content: value })
      setInput('')
    } catch {
      setInput(value)
    }
  }

  async function handleNewChat() {
    if (!activeWorkspace || createSession.isPending) return
    const session = await createSession.mutateAsync({ workspaceId: activeWorkspace.id })
    setActiveSessionId(session.id)
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
            ) : createSession.error || sendMessage.error ? (
              <EmptyChatState title="Message was not sent" description="The draft is still in the input. Check the API connection and try again." />
            ) : isLoadingSessions || isLoadingSession ? (
              <EmptyChatState title="Loading Chat" description="Fetching persisted Chat Sessions and messages." />
            ) : messages.length === 0 ? (
              <EmptyChatState title="Ask a strategic question" description="Messages will be persisted to this Workspace-scoped Chat Session." />
            ) : (
              messages.map((message) =>
                message.role === 'user' ? (
                  <UserBubble key={message.id} content={message.content} />
                ) : (
                  <AssistantCard key={message.id} message={message} />
                ),
              )
            )}

            {isThinking && (
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
              <CommandChip command="/brief" label="Generate Brief" />
              <CommandChip command="/sources" label="View Sources" />
              <CommandChip command="/trace" label="View Trace" />
              <span className="ml-auto">Copilot can make mistakes. Consider verifying.</span>
            </div>
          </div>
        </form>
      </section>

      <SourcesPanel sessions={sessions} activeSessionId={activeSessionId} onSelectSession={setActiveSessionId} />
    </div>
  )
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[65%] rounded-[16px_16px_4px_16px] bg-user-bubble px-5 py-4 text-sm leading-7 text-foreground shadow-sm">{content}</div>
    </div>
  )
}

function AssistantCard({ message }: { message: ChatMessage }) {
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

          <div className="mt-7 rounded-xl border border-border bg-surface-subtle p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <FileText className="h-4 w-4" />
              Cited Evidence
            </div>
            <div className="flex flex-wrap gap-3">
              <EvidenceChip icon="csv" label="Pending Task 6" />
            </div>
          </div>

          <p className="mt-7 text-sm leading-7 text-foreground">
            This response is persisted. Source-grounded evidence, citations, and confidence gaps are added in Task 6.
          </p>

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
        </div>
      </div>
    </article>
  )
}

function EvidenceChip({ icon, label }: { icon: 'csv' | 'pdf'; label: string }) {
  const Icon = icon === 'csv' ? FileSpreadsheet : FileText
  const color = icon === 'csv' ? 'text-status-ready-foreground' : 'text-status-failed-foreground'
  return (
    <span className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 font-mono text-xs text-foreground shadow-sm">
      <Icon className={`h-4 w-4 ${color}`} />
      {label}
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
}: {
  sessions: { id: number; title: string; updatedAt: string }[]
  activeSessionId: number | null
  onSelectSession: (id: number) => void
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
        <SourceCard
          type="csv"
          name="Source citations"
          badge="Task 6"
          quote="Sources Used will show persisted Source Citations after AI Consultant responses are implemented."
        />
      </div>

      <div className="border-t border-border bg-card px-6 py-5">
        <PanelLink label="Trace Reference" />
        <PanelLink label="Drafted Briefs" />
      </div>
    </aside>
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

function SourceCard({ type, name, badge, quote }: { type: 'pdf' | 'csv'; name: string; badge: string; quote: string }) {
  const Icon = type === 'pdf' ? FileText : FileSpreadsheet
  const color = type === 'pdf' ? 'text-status-failed-foreground' : 'text-status-ready-foreground'
  return (
    <article className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className={`h-4 w-4 shrink-0 ${color}`} />
          <h3 className="truncate text-sm font-semibold text-foreground">{name}</h3>
        </div>
        <span className="rounded bg-chip-gray px-2 py-1 font-mono text-[11px] text-text-hint">{badge}</span>
      </div>
      <blockquote className="border-l-2 border-border pl-4 text-sm italic leading-6 text-muted-foreground">“{quote}”</blockquote>
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
