import { X } from 'lucide-react'
import type { AgentToolCall, MessageSourceCitation } from '../../../types/chat'
import { PanelLink } from './PanelLink'
import { SessionSources } from './SessionSources'
import { formatDate } from './utils'

export function SourcesPanel({
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
