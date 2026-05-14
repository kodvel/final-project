import { createFileRoute } from '@tanstack/react-router'
import { AlertTriangle, CalendarDays, CircleHelp, FileText, Lightbulb, RefreshCw, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'
import { useEffect, useId, useMemo, useState } from 'react'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { useRefreshVisualizationSnapshot, useVisualizationSnapshot } from '../features/visualization-data/hooks'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { VisualizationEvidenceRef, VisualizationSnapshotListItem, VisualizationSourceCard } from '../types/visualization'

export const Route = createFileRoute('/visualization-data')({
  component: VisualizationDataPage,
})

function VisualizationDataPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? 0

  const [periodStartMonth, setPeriodStartMonth] = useState('')
  const [periodEndMonth, setPeriodEndMonth] = useState('')

  useEffect(() => {
    const now = new Date()
    const defaultEnd = toMonthInputValue(now)
    const defaultStart = toMonthInputValue(new Date(now.getFullYear(), now.getMonth() - 5, 1))
    setPeriodStartMonth((value) => value || defaultStart)
    setPeriodEndMonth((value) => value || defaultEnd)
  }, [])

  const hasValidRange = periodStartMonth.length > 0 && periodEndMonth.length > 0 && periodStartMonth <= periodEndMonth
  const queryParams = useMemo(
    () => ({
      workspaceId,
      periodStartMonth,
      periodEndMonth,
    }),
    [periodEndMonth, periodStartMonth, workspaceId],
  )

  const { data: snapshot, isLoading, error, isFetching } = useVisualizationSnapshot(queryParams)
  const refreshSnapshot = useRefreshVisualizationSnapshot()

  if (!activeWorkspace) {
    return (
      <div className="h-full overflow-auto p-8">
        <EmptyState title="Select a Workspace" description="Choose or create a Workspace from the sidebar before viewing Visualizations." />
      </div>
    )
  }

  if (!hasValidRange) {
    return (
      <div className="h-full overflow-auto p-8">
        <EmptyState
          title="Pick a valid month range"
          description="Visualization Data now loads a cached snapshot for one Workspace and one month range."
        />
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full overflow-auto p-8">
        <ErrorState message="Could not load the Visualization Snapshot. Check that the API is running." />
      </div>
    )
  }

  if (isLoading && !snapshot) {
    return (
      <div className="h-full overflow-auto p-8">
        <LoadingState />
      </div>
    )
  }

  const content = snapshot?.contentJson
  const coverage = content?.coverage
  const executiveSummary = content?.executive_summary
  const confidenceAssessment = content?.confidence_assessment
  const crossSourcePatterns = content?.cross_source_patterns ?? []
  const sourceCards = content?.source_cards ?? []
  const keyFindings = content?.key_findings ?? []
  const risksAssumptions = content?.risks_assumptions ?? []
  const opportunities = content?.opportunities ?? []
  const gaps = content?.gaps ?? []
  const sourceCount = sourceCards.length || snapshot?.sourceIds?.length || coverage?.readySources || 0
  const refreshPending = refreshSnapshot.isPending || isFetching

  return (
    <div className="h-full overflow-auto p-8 text-foreground">
      <div className="mb-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            <CalendarDays className="h-4 w-4" />
            Visualization Snapshot
          </div>
          <div>
            <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">AI-Curated Insight Board</h1>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Cached intelligence for {formatMonthRange(periodStartMonth, periodEndMonth)} across the active Workspace.
            </p>
          </div>
          {snapshot?.status && (
            <Badge variant="outline" className="w-fit border-border bg-surface-subtle text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              {snapshot.status}
            </Badge>
          )}
        </div>

        <div className="flex flex-col gap-3 lg:items-end">
          <div className="flex flex-wrap items-end gap-3">
            <MonthInput label="Start month" value={periodStartMonth} onChange={setPeriodStartMonth} />
            <MonthInput label="End month" value={periodEndMonth} onChange={setPeriodEndMonth} />
            <Button
              variant="outline"
              onClick={() => refreshSnapshot.mutate(queryParams)}
              disabled={!hasValidRange || refreshPending}
              className="border-border bg-background"
            >
              <RefreshCw className={`h-4 w-4 ${refreshPending ? 'animate-spin' : ''}`} />
              {refreshPending ? 'Refreshing' : 'Refresh'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            {snapshot?.generatedAt
              ? `Updated ${formatTimestamp(snapshot.generatedAt)}`
              : 'Snapshot regenerates on demand for the selected month range.'}
          </p>
        </div>
      </div>

      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Coverage"
            value={String(coverage?.totalSources ?? sourceCount)}
            helper={coverage?.summary ?? 'Ready sources only'}
            accent="indigo"
          />
          <MetricCard
            label="Ready Sources"
            value={String(coverage?.readySources ?? sourceCount)}
            helper="Composed into the snapshot"
            accent="emerald"
          />
          <MetricCard label="Excluded" value={String(coverage?.excludedSources ?? 0)} helper="Filtered out by scope or readiness" accent="amber" />
          <MetricCard label="Range" value={formatMonthRange(periodStartMonth, periodEndMonth)} helper="Workspace-scoped and cached" accent="slate" />
        </section>

        <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
          <SectionHeader
            eyebrow="Executive summary"
            title="Cross-artifact intelligence snapshot"
            description="LLM-composed view across ready Sources, teams, labels, and artifacts in this period."
            icon={<Sparkles className="h-4 w-4" />}
          />
          {executiveSummary ? (
            <div className="mt-5 rounded-xl border border-border bg-surface-subtle p-5">
              <p className="text-sm leading-7 text-foreground">{executiveSummary}</p>
              {confidenceAssessment && (
                <div className="mt-4 inline-flex max-w-full items-start gap-1 rounded-md border border-border bg-background px-2.5 py-0.5 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                  <span className="min-w-0 whitespace-normal break-words">
                    {confidenceAssessment}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <EmptyInline title="No executive summary" description="The snapshot did not include a cross-artifact summary yet." className="mt-5" />
          )}
        </section>

        <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
          <SectionHeader
            eyebrow="Cross-source patterns"
            title="Signals across teams and labels"
            description="Patterns are synthesized across multiple Source Artifacts, not listed per file."
            icon={<Sparkles className="h-4 w-4" />}
          />
          <ItemList
            items={crossSourcePatterns}
            emptyTitle="No cross-source patterns"
            emptyDescription="The snapshot did not find repeated or conflicting signals across sources."
            className="mt-5"
          />
        </section>

        <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
          <SectionHeader
            eyebrow="Coverage overview"
            title="What this snapshot includes"
            description={coverage?.summary ?? 'Ready sources overlapping the selected month range are composed into one cached intelligence view.'}
          />
          {coverage?.notes && coverage.notes.length > 0 && (
            <ul className="mt-4 space-y-2 text-sm leading-6 text-muted-foreground">
              {coverage.notes.map((note) => (
                <li key={note} className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
          <SectionHeader
            eyebrow="Source cards"
            title="Ready sources in range"
            description="Each card summarizes one source used to build the snapshot."
          />
          {sourceCards.length > 0 ? (
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {sourceCards.map((card) => (
                <SourceCard key={card.sourceId ?? card.title} card={card} />
              ))}
            </div>
          ) : (
            <EmptyInline title="No source cards" description="The selected range did not return any ready overlapping sources." />
          )}
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
            <SectionHeader
              eyebrow="Key findings"
              title="Most important takeaways"
              description="Snapshot-level conclusions grounded in the underlying sources."
              icon={<Sparkles className="h-4 w-4" />}
            />
            <ItemList
              items={keyFindings}
              emptyTitle="No key findings"
              emptyDescription="The snapshot did not surface any key findings for this range."
              className="mt-5"
            />
          </section>

          <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
            <SectionHeader
              eyebrow="Risks / assumptions"
              title="What could be wrong"
              description="Risks and assumptions are shown together so gaps stay visible in context."
              icon={<AlertTriangle className="h-4 w-4" />}
            />
            <ItemList
              items={risksAssumptions}
              emptyTitle="No risks or assumptions"
              emptyDescription="The snapshot did not include explicit risks or assumptions."
              className="mt-5"
            />
          </section>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
            <SectionHeader
              eyebrow="Opportunities"
              title="Potential moves"
              description="Concrete opportunities highlighted by the snapshot."
              icon={<Lightbulb className="h-4 w-4" />}
            />
            <ItemList
              items={opportunities}
              emptyTitle="No opportunities"
              emptyDescription="The snapshot did not include opportunity items for this range."
              className="mt-5"
            />
          </section>

          <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
            <SectionHeader
              eyebrow="Gaps"
              title="Missing evidence"
              description="Explicit gaps help show where the current snapshot is incomplete."
              icon={<CircleHelp className="h-4 w-4" />}
            />
            <ItemList
              items={gaps}
              emptyTitle="No gaps"
              emptyDescription="The snapshot did not surface missing evidence or unresolved questions."
              className="mt-5"
            />
          </section>
        </section>
      </div>
    </div>
  )
}

function SectionHeader({ eyebrow, title, description, icon }: { eyebrow: string; title: string; description: string; icon?: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      {icon ? <div className="mt-0.5 text-muted-foreground">{icon}</div> : null}
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{eyebrow}</p>
        <h2 className="mt-1 font-heading text-lg font-semibold text-foreground">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  helper,
  accent,
}: {
  label: string
  value: string
  helper: string
  accent: 'indigo' | 'emerald' | 'amber' | 'slate'
}) {
  const accentMap = {
    indigo: 'border-l-primary bg-primary/5',
    emerald: 'border-l-emerald-500 bg-emerald-500/5',
    amber: 'border-l-amber-500 bg-amber-500/5',
    slate: 'border-l-slate-400 bg-slate-400/5',
  }

  return (
    <div className={`rounded-2xl border border-border border-l-4 p-5 shadow-sm ${accentMap[accent]}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className="mt-3 font-heading text-2xl font-semibold text-foreground">{value}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{helper}</p>
    </div>
  )
}

function MonthInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const inputId = useId()

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </label>
      <Input id={inputId} type="month" value={value} onChange={(event) => onChange(event.target.value)} className="w-[170px] bg-background" />
    </div>
  )
}

function SourceCard({ card }: { card: VisualizationSourceCard }) {
  return (
    <article className="rounded-2xl border border-border bg-surface-subtle p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-border bg-background text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              {card.sourceFileType ?? 'source'}
            </Badge>
            {card.periodLabel && (
              <Badge variant="outline" className="border-border bg-background text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                {card.periodLabel}
              </Badge>
            )}
          </div>
          <h3 className="font-heading text-base font-semibold text-foreground">{card.title}</h3>
        </div>
        <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
        {card.teamLabel && (
          <Badge variant="secondary" className="bg-primary/10 text-primary">
            {formatLabel(card.teamLabel)}
          </Badge>
        )}
        {card.categoryLabels?.map((category) => (
          <Badge key={category} variant="outline" className="border-border bg-background text-muted-foreground">
            {formatLabel(category)}
          </Badge>
        ))}
      </div>

      {card.summary && <p className="mt-4 text-sm leading-6 text-muted-foreground">{card.summary}</p>}

      {card.evidenceRefs && card.evidenceRefs.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {card.evidenceRefs.map((ref) => (
            <EvidenceBadge key={evidenceRefKey(ref)} refItem={ref} />
          ))}
        </div>
      )}
    </article>
  )
}

function ItemList({
  items,
  emptyTitle,
  emptyDescription,
  className,
}: {
  items: VisualizationSnapshotListItem[]
  emptyTitle: string
  emptyDescription: string
  className?: string
}) {
  if (items.length === 0) {
    return <EmptyInline className={className} title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className={`space-y-3 ${className ?? ''}`}>
      {items.map((item) => (
        <div key={itemKey(item)} className="rounded-xl border border-border bg-surface-subtle p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              {item.kind && (
                <Badge variant="outline" className="border-border bg-background text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  {item.kind}
                </Badge>
              )}
              {item.theme && (
                <Badge variant="secondary" className="bg-primary/10 text-primary">
                  {formatLabel(item.theme)}
                </Badge>
              )}
              <p className="text-sm leading-6 text-foreground">{item.title ?? item.text ?? item.detail ?? item.description ?? 'Untitled item'}</p>
            </div>
            {item.confidence != null && <span className="text-xs capitalize text-muted-foreground">{formatConfidence(item.confidence)}</span>}
          </div>
          {item.evidenceRefs && item.evidenceRefs.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {item.evidenceRefs.map((ref) => (
                <EvidenceBadge key={evidenceRefKey(ref)} refItem={ref} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function EvidenceBadge({ refItem }: { refItem: VisualizationEvidenceRef }) {
  const label =
    refItem.quote ?? (refItem.pageNumber != null ? `p.${refItem.pageNumber}` : (refItem.sourceTitle ?? `Source ${refItem.sourceId ?? 'ref'}`))
  return (
    <Badge variant="outline" className="max-w-full border-border bg-background text-[11px] font-normal text-muted-foreground">
      <span className="truncate">{label}</span>
    </Badge>
  )
}

function EmptyInline({ title, description, className }: { title: string; description: string; className?: string }) {
  return (
    <div className={`rounded-xl border border-dashed border-border p-5 text-center ${className ?? ''}`}>
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
    </div>
  )
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-border bg-background p-10 text-center shadow-sm">
      <h3 className="font-heading text-lg font-semibold text-foreground">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
    </section>
  )
}

function LoadingState() {
  return (
    <section className="p-8 ">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />

        <div>
          <p className="font-medium text-foreground">Preparing visualizations</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Analyzing data and building charts...
          </p>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
        <div className="h-32 animate-pulse rounded-xl bg-muted" />
      </div>
    </section>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <section className="rounded-2xl border border-status-failed bg-status-failed-light p-8 text-sm text-status-failed shadow-sm">{message}</section>
  )
}

function toMonthInputValue(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function formatMonthRange(startMonth: string, endMonth: string) {
  return startMonth && endMonth ? `${startMonth} → ${endMonth}` : 'Select a month range'
}

function formatTimestamp(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatLabel(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatConfidence(value: VisualizationSnapshotListItem['confidence']) {
  if (typeof value === 'number') return `${Math.round(value * 100)}%`
  return String(value)
}

function itemKey(item: VisualizationSnapshotListItem) {
  return [item.kind, item.theme ?? '', item.title ?? item.text ?? item.detail ?? item.description ?? 'item', item.confidence ?? ''].join('|')
}

function evidenceRefKey(ref: VisualizationEvidenceRef) {
  return [ref.sourceId ?? '', ref.artifactId ?? '', ref.sourceTitle ?? '', ref.pageNumber ?? '', ref.quote ?? ''].join('|')
}
