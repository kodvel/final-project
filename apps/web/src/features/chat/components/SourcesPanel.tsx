import { ChevronRight } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import type { AgentToolCall, MessageSourceCitation } from '../../../types/chat'
import { SourceGroupCard } from './SourceGroupCard'
import { formatDate, groupCitations } from './utils'

function CollapsibleContent({
  id,
  open,
  className,
  children,
}: {
  id: string
  open: boolean
  className: string
  children: ReactNode
}) {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = contentRef.current
    if (!element) return

    if (open) {
      element.removeAttribute('inert')
    } else {
      element.setAttribute('inert', '')
    }
  }, [open])

  return (
    <div
      id={id}
      ref={contentRef}
      aria-hidden={!open}
      inert={!open || undefined}
      className={`grid overflow-hidden transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none ${open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}
    >
      <div className={`min-h-0 overflow-hidden ${className}`}>{children}</div>
    </div>
  )
}

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
  // Recent Sessions – render all sessions, scroll inside the section
  const recentSessionsTitleId = useId()
  const recentSessionsListId = useId()

  // Sources – combined uploaded + web, accordion
  const citationGroups = groupCitations(citations)
  const hasSources = citations.length > 0
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const sourcesPanelId = useId()

  // Tool Calls – accordion
  const hasToolCalls = toolCalls.length > 0
  const [toolCallsOpen, setToolCallsOpen] = useState(false)
  const toolCallsPanelId = useId()

  const sectionHeaderClassName =
    'flex w-full items-center justify-between bg-white px-5 py-4 text-left transition-colors duration-200 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20'

  const sectionLabelClassName = 'text-[10px] font-semibold uppercase tracking-[0.24em] text-text-hint'

  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-col bg-surface-subtle">
      <header className="border-b border-border/50 bg-white px-5 py-4">
        <h2 className="font-heading text-[16px] font-semibold text-foreground">Sources Panel</h2>
        <p className="mt-1 text-xs text-text-hint">Citations and session context for this conversation</p>
      </header>

      <div className="flex min-h-0 flex-1 flex-col">
        <section aria-labelledby={recentSessionsTitleId} className="flex min-h-0 flex-1 flex-col px-4 py-4">
          <p id={recentSessionsTitleId} className={`${sectionLabelClassName} mb-2 shrink-0`}>
            Sessions ({sessions.length})
          </p>
          <div id={recentSessionsListId} className="min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-1">
            {sessions.length === 0 ? (
              <p className="px-3 py-2.5 text-xs text-text-hint">No sessions yet.</p>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => onSelectSession(session.id)}
                  className={`group w-full rounded-lg border px-3 py-2.5 text-left transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 ${
                    activeSessionId === session.id
                      ? 'border-primary/20 bg-primary/5 text-foreground shadow-sm'
                      : 'border-transparent bg-transparent text-muted-foreground hover:border-border/60 hover:bg-white/70 hover:text-foreground'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="block min-w-0 flex-1 truncate text-sm font-medium transition-colors duration-200 group-hover:text-primary">
                      {session.title}
                    </span>
                    <span className="shrink-0 rounded-full bg-chip-gray px-2 py-0.5 font-mono text-[10px] text-text-hint">
                      #{session.id}
                    </span>
                  </div>
                  <span className="mt-1 block font-mono text-xs uppercase tracking-[0.12em] text-text-hint">{formatDate(session.updatedAt)}</span>
                </button>
              ))
            )}
          </div>
        </section>

        <div className="shrink-0 flex flex-col divide-y divide-border/60 border-t border-border/50">
          {/* Sources (combined uploaded + web) */}
          {hasSources && (
            <section>
              <button
                type="button"
                onClick={() => setSourcesOpen(!sourcesOpen)}
                aria-expanded={sourcesOpen}
                aria-controls={sourcesPanelId}
                className={sectionHeaderClassName}
              >
                <span className={sectionLabelClassName}>Sources</span>
                <ChevronRight
                  className={`h-4 w-4 shrink-0 text-text-hint transition-transform duration-200 ${sourcesOpen ? 'rotate-90' : ''}`}
                />
              </button>
              <CollapsibleContent id={sourcesPanelId} open={sourcesOpen} className="p-0">
                <div className="space-y-2">
                  {citationGroups.map((group) => {
                    const firstCitation = group.citations[0]
                    const isWeb = firstCitation.citationType === 'web'
                    const type: 'pdf' | 'csv' | 'web' = isWeb
                      ? 'web'
                      : group.title.toLowerCase().endsWith('.pdf')
                        ? 'pdf'
                        : 'csv'
                    return <SourceGroupCard key={group.key} group={group} type={type} />
                  })}
                </div>
              </CollapsibleContent>
            </section>
          )}

          {/* Tool Calls */}
          {hasToolCalls && (
            <section>
              <button
                type="button"
                onClick={() => setToolCallsOpen(!toolCallsOpen)}
                aria-expanded={toolCallsOpen}
                aria-controls={toolCallsPanelId}
                className={sectionHeaderClassName}
              >
                <span className={sectionLabelClassName}>Tool Calls</span>
                <ChevronRight
                  className={`h-4 w-4 shrink-0 text-text-hint transition-transform duration-200 ${toolCallsOpen ? 'rotate-90' : ''}`}
                />
              </button>
              <CollapsibleContent id={toolCallsPanelId} open={toolCallsOpen} className="p-0">
                <div className="space-y-1.5">
                  {toolCalls.map((tc) => (
                    <div
                      key={tc.id}
                      className="rounded-lg border border-transparent px-3 py-2.5 text-xs text-muted-foreground transition-colors duration-200 hover:border-border/60 hover:bg-slate-50"
                    >
                      <span className="font-mono uppercase tracking-[0.12em] text-text-hint">{tc.status}</span>{' '}
                      <span className="font-semibold text-foreground">{tc.toolName}</span>
                      {tc.summary && <span className="ml-1">— {tc.summary}</span>}
                    </div>
                  ))}
                </div>
              </CollapsibleContent>
            </section>
          )}
        </div>
      </div>
    </aside>
  )
}
