import { ChevronRight } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import type { AgentToolCall, ChatMessage, MessageSourceCitation } from '../../../types/chat'
import { SourceGroupCard } from './SourceGroupCard'
import { formatDate, groupCitations } from './utils'

const INITIAL_SESSIONS_SHOWN = 3

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
  messages,
  onScrollToMessage,
}: {
  sessions: { id: number; title: string; updatedAt: string }[]
  activeSessionId: number | null
  onSelectSession: (id: number) => void
  citations: MessageSourceCitation[]
  toolCalls: AgentToolCall[]
  messages: ChatMessage[]
  onScrollToMessage: (messageId: number) => void
}) {
  // Recent Sessions – show 3 initially, toggle show more / less
  const [showAllSessions, setShowAllSessions] = useState(false)
  const visibleSessions = showAllSessions ? sessions : sessions.slice(0, INITIAL_SESSIONS_SHOWN)
  const hasMoreSessions = sessions.length > INITIAL_SESSIONS_SHOWN
  const recentSessionsTitleId = useId()
  const recentSessionsListId = useId()

  // Drafted Briefs – accordion, auto-opens when a new brief arrives
  const decisionBriefMessages = messages.filter(
    (m) => m.messageType === 'decision_brief' && m.decisionBriefId != null,
  )
  const [briefsOpen, setBriefsOpen] = useState(false)
  const briefsPanelId = useId()
  const prevBriefCountRef = useRef(0)
  useEffect(() => {
    if (decisionBriefMessages.length > prevBriefCountRef.current && decisionBriefMessages.length > 0) {
      setBriefsOpen(true)
    }
    prevBriefCountRef.current = decisionBriefMessages.length
  }, [decisionBriefMessages.length])

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
        <div className="flex-1 overflow-auto px-4 py-4">
        {/* Recent Sessions */}
        <section aria-labelledby={recentSessionsTitleId}>
          <div className="mb-2 flex items-center justify-between gap-3">
            <p id={recentSessionsTitleId} className={sectionLabelClassName}>
              Recent Sessions
            </p>
            {hasMoreSessions && (
              <button
                type="button"
                onClick={() => setShowAllSessions(!showAllSessions)}
                aria-expanded={showAllSessions}
                aria-controls={recentSessionsListId}
                className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium text-text-hint transition-colors duration-200 hover:bg-white/70 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
              >
                {showAllSessions ? 'Show less' : `Show more`}
                <ChevronRight className={`h-3.5 w-3.5 transition-transform duration-200 ${showAllSessions ? 'rotate-90' : ''}`} />
              </button>
            )}
          </div>
          <div id={recentSessionsListId} className="space-y-1.5">
            {visibleSessions.map((session) => (
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
                <span className="block truncate text-sm font-medium transition-colors duration-200 group-hover:text-primary">{session.title}</span>
                <span className="mt-1 block font-mono text-xs uppercase tracking-[0.12em] text-text-hint">{formatDate(session.updatedAt)}</span>
              </button>
            ))}
          </div>
        </section>
        </div>

        <div className="shrink-0 flex flex-col divide-y divide-border/60 border-t border-border/50">
          {/* Drafted Briefs */}
          {decisionBriefMessages.length > 0 && (
            <section>
              <button
                type="button"
                onClick={() => setBriefsOpen(!briefsOpen)}
                aria-expanded={briefsOpen}
                aria-controls={briefsPanelId}
                className={sectionHeaderClassName}
              >
                <span className={sectionLabelClassName}>Briefs</span>
                <ChevronRight
                  className={`h-4 w-4 shrink-0 text-text-hint transition-transform duration-200 ${briefsOpen ? 'rotate-90' : ''}`}
                />
              </button>
              <CollapsibleContent id={briefsPanelId} open={briefsOpen} className="p-0">
                <div className="space-y-1.5">
                  {decisionBriefMessages.map((m, i) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => onScrollToMessage(m.id)}
                      className="w-full rounded-lg border border-transparent px-3 py-2.5 text-left text-xs font-medium text-muted-foreground transition-colors duration-200 hover:border-border/60 hover:bg-slate-50 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
                    >
                      {`#${i + 1}`} { m.decisionBriefTitle ?? `Decision Brief #${m.decisionBriefId}`}
                    </button>
                  ))}
                </div>
              </CollapsibleContent>
            </section>
          )}

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
