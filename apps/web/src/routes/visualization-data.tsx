import { createFileRoute, Link } from '@tanstack/react-router'
import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  CircleHelp,
  Download,
  Lightbulb,
  Maximize2,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import {
  ChartModule,
  EmptyInline,
  EmptyState,
  ErrorState,
  FilterSelect,
  InsightMiniCard,
  KpiCard,
  LoadingState,
  MonthInput,
  PdfInsightCard,
  SectionHeader,
  SnapshotStatusBadge,
} from '../features/visualization-data/components'
import { useRefreshVisualizationSnapshot, useVisualizationSnapshot } from '../features/visualization-data/hooks'
import { buildChartSeries, formatConfidence, formatLabel, formatMonthRange, formatTimestamp, getDefaultMonthRange, itemKey, uniqueLabels } from '../features/visualization-data/utils'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'

export const Route = createFileRoute('/visualization-data')({
  component: VisualizationDataPage,
})

function VisualizationDataPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? 0
  const defaultMonthRange = useMemo(() => getDefaultMonthRange(), [])

  const [periodStartMonth, setPeriodStartMonth] = useState(() => defaultMonthRange.start)
  const [periodEndMonth, setPeriodEndMonth] = useState(() => defaultMonthRange.end)
  const [selectedTeam, setSelectedTeam] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [chartExpanded, setChartExpanded] = useState(false)

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
  const totalSourceCount = sourceCards.length || snapshot?.sourceIds?.length || coverage?.totalSources || 0

  const teamOptions = useMemo(() => uniqueLabels(sourceCards.flatMap((card) => (card.teamLabel ? [card.teamLabel] : []))), [sourceCards])
  const categoryOptions = useMemo(() => uniqueLabels(sourceCards.flatMap((card) => card.categoryLabels ?? [])), [sourceCards])

  useEffect(() => {
    if (selectedTeam !== 'all' && !teamOptions.includes(selectedTeam)) setSelectedTeam('all')
  }, [selectedTeam, teamOptions])

  useEffect(() => {
    if (selectedCategory !== 'all' && !categoryOptions.includes(selectedCategory)) setSelectedCategory('all')
  }, [categoryOptions, selectedCategory])

  const visibleSourceCards = useMemo(
    () =>
      sourceCards.filter((card) => {
        const teamMatches = selectedTeam === 'all' || card.teamLabel === selectedTeam
        const categoryMatches = selectedCategory === 'all' || Boolean(card.categoryLabels?.some((category) => category === selectedCategory))
        return teamMatches && categoryMatches
      }),
    [selectedCategory, selectedTeam, sourceCards],
  )

  const filteredSourceCount = visibleSourceCards.length
  const readyCoveragePct = coverage?.totalSources ? Math.round(((coverage?.readySources ?? 0) / coverage.totalSources) * 100) : null
  const crossSourceCount = crossSourcePatterns.length
  const riskCount = risksAssumptions.length + gaps.length
  const chartSeries = useMemo(
    () =>
      buildChartSeries(periodStartMonth, periodEndMonth, {
        sourceCount: totalSourceCount,
        patternCount: crossSourceCount,
        gapCount: riskCount,
        expanded: chartExpanded,
      }),
    [chartExpanded, crossSourceCount, periodEndMonth, periodStartMonth, riskCount, totalSourceCount],
  )

  const topInsight =
    executiveSummary ?? crossSourcePatterns[0]?.text ?? keyFindings[0]?.text ?? coverage?.summary ?? 'No executive summary has been generated yet.'

  const refreshPending = refreshSnapshot.isPending || isFetching

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
          description="Visualization Data loads one cached snapshot for one Workspace and one month range."
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

  return (
    <div className="h-full min-w-0 overflow-auto bg-white px-6 py-7 text-foreground lg:px-8 lg:py-8">
      <div className="space-y-7">
        <header className="flex flex-col gap-5 border-b border-border/70 pb-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-[11px] font-medium text-indigo-700">
              <CalendarDays className="h-3.5 w-3.5" />
              Visualization Snapshot
            </div>
            <div className="space-y-2">
              <h1 className="font-heading text-3xl font-semibold tracking-tight text-foreground">AI-Curated Insight Board</h1>
              <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                Synthesized intelligence from connected CSV and PDF data sources for {formatMonthRange(periodStartMonth, periodEndMonth)}.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {snapshot?.status && <SnapshotStatusBadge status={snapshot.status} />}
              <Badge variant="outline" className="border-border bg-surface-subtle text-[11px] text-muted-foreground">
                {activeWorkspace.name}
              </Badge>
              <Badge variant="secondary" className="bg-primary/10 text-primary">
                {filteredSourceCount} of {sourceCards.length || totalSourceCount} sources in focus
              </Badge>
            </div>
          </div>

          <div className="w-full xl:max-w-[760px]">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <FilterSelect label="Team" value={selectedTeam} onChange={setSelectedTeam} options={teamOptions} placeholder="All teams" />
              <FilterSelect
                label="Category"
                value={selectedCategory}
                onChange={setSelectedCategory}
                options={categoryOptions}
                placeholder="All categories"
              />
              <MonthInput label="Period start" value={periodStartMonth} onChange={setPeriodStartMonth} />
              <MonthInput label="Period end" value={periodEndMonth} onChange={setPeriodEndMonth} />
              <Button
                variant="outline"
                onClick={() => refreshSnapshot.mutate(queryParams)}
                disabled={!hasValidRange || refreshPending}
                className="w-full border-border bg-white transition hover:bg-surface-subtle sm:col-span-2 xl:col-span-1"
              >
                <RefreshCw className={`h-4 w-4 ${refreshPending ? 'animate-spin' : ''}`} />
                {refreshPending ? 'Refreshing' : 'Refresh'}
              </Button>
            </div>

            <div className="mt-3 flex flex-col gap-1 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
              <p>
                {selectedTeam !== 'all' || selectedCategory !== 'all'
                  ? `Focused on ${selectedTeam === 'all' ? 'all teams' : formatLabel(selectedTeam)} · ${
                      selectedCategory === 'all' ? 'all categories' : formatLabel(selectedCategory)
                    }`
                  : 'Workspace-scoped snapshot with quick-focus filters.'}
              </p>
              <p>{snapshot?.generatedAt ? `Updated ${formatTimestamp(snapshot.generatedAt)}` : 'Snapshot regenerates on demand.'}</p>
            </div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-3">
          <KpiCard
            label="Ready coverage"
            value={readyCoveragePct != null ? `${readyCoveragePct}%` : String(coverage?.readySources ?? totalSourceCount)}
            detail={`${coverage?.readySources ?? totalSourceCount} ready source${(coverage?.readySources ?? totalSourceCount) === 1 ? '' : 's'} in the snapshot`}
            accent="indigo"
          />
          <KpiCard
            label="Cross-source signals"
            value={String(crossSourceCount)}
            detail="Repeated or conflicting patterns synthesized across teams and labels"
            accent="emerald"
          />
          <KpiCard
            label="Open gaps"
            value={String(riskCount)}
            detail="Risks, assumptions, and missing evidence that still need follow-up"
            accent="amber"
          />
        </section>

        <section
          className={cn(
            'overflow-hidden rounded-[24px] border border-border bg-white shadow-sm transition-all duration-200',
            chartExpanded ? 'min-h-[520px]' : 'min-h-[430px]',
          )}
        >
          <div className="flex flex-col gap-4 border-b border-border/70 px-6 py-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <TrendingUp className="h-4 w-4" />
                Snapshot trajectory
              </div>
              <h2 className="font-heading text-xl font-semibold text-foreground">Signal density vs projected baseline</h2>
              <p className="text-sm leading-6 text-muted-foreground">
                Monthly composition across ready Source Artifacts for the selected Workspace and period range.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:bg-surface-subtle hover:text-foreground">
                <Download className="h-4 w-4" />
                Download
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setChartExpanded((value) => !value)}
                className="text-muted-foreground hover:bg-surface-subtle hover:text-foreground"
              >
                <Maximize2 className="h-4 w-4" />
                {chartExpanded ? 'Collapse' : 'Expand'}
              </Button>
            </div>
          </div>

          <div className="px-6 pb-6 pt-5">
            <ChartModule series={chartSeries} />

            <div className="mt-5 flex flex-col gap-4 rounded-2xl border border-border bg-surface-subtle p-4 md:flex-row md:items-start md:justify-between">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 rounded-full bg-primary/10 p-2 text-primary">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">Key insight</p>
                  <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{topInsight}</p>
                  {confidenceAssessment && <p className="text-xs text-muted-foreground">Confidence: {confidenceAssessment}</p>}
                </div>
              </div>

              <Button asChild size="sm" className="self-start bg-primary text-primary-foreground shadow-sm hover:bg-primary/90">
                <Link to="/chat">
                  Ask in Chat
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="rounded-[24px] border border-border bg-white p-6 shadow-sm">
          <SectionHeader
            eyebrow="Insight cards"
            title="Strategic synthesis"
            description="Snapshot-level conclusions grounded in the selected period, not per-file noise."
            icon={<Sparkles className="h-4 w-4" />}
          />

          {executiveSummary ? (
            <div className="mt-5 rounded-2xl border border-border bg-surface-subtle p-5">
              <p className="text-sm leading-7 text-foreground">{executiveSummary}</p>
            </div>
          ) : (
            <EmptyInline className="mt-5" title="No executive summary" description="The snapshot did not include a cross-artifact summary yet." />
          )}

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <InsightMiniCard
              title="Key findings"
              icon={<TrendingUp className="h-4 w-4" />}
              items={keyFindings}
              tone="indigo"
              emptyTitle="No findings"
            />
            <InsightMiniCard
              title="Risks & assumptions"
              icon={<AlertTriangle className="h-4 w-4" />}
              items={risksAssumptions}
              tone="amber"
              emptyTitle="No risks or assumptions"
            />
            <InsightMiniCard
              title="Opportunities"
              icon={<Lightbulb className="h-4 w-4" />}
              items={opportunities}
              tone="emerald"
              emptyTitle="No opportunities"
            />
            <InsightMiniCard title="Gaps" icon={<CircleHelp className="h-4 w-4" />} items={gaps} tone="rose" emptyTitle="No gaps" />
          </div>
        </section>

        <section className="rounded-[24px] border border-border bg-white p-6 shadow-sm">
          <SectionHeader
            eyebrow="Cross-source patterns"
            title="Signals across teams and labels"
            description="Patterns synthesized across multiple Source Artifacts, not listed per file."
            icon={<Sparkles className="h-4 w-4" />}
          />
          {crossSourcePatterns.length > 0 ? (
            <div className="mt-5 space-y-3">
              {crossSourcePatterns.map((item) => (
                <div key={itemKey(item)} className="rounded-2xl border border-border bg-surface-subtle p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {item.kind && (
                          <Badge variant="outline" className="border-border bg-white text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                            {item.kind}
                          </Badge>
                        )}
                        {item.theme && (
                          <Badge variant="secondary" className="bg-primary/10 text-primary">
                            {formatLabel(item.theme)}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm leading-6 text-foreground">{item.title ?? item.text ?? item.detail ?? item.description ?? 'Untitled item'}</p>
                    </div>
                    {item.confidence != null && <span className="text-xs capitalize text-muted-foreground">{formatConfidence(item.confidence)}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyInline
              className="mt-5"
              title="No cross-source patterns"
              description="The snapshot did not find repeated or conflicting signals across sources."
            />
          )}
        </section>

        <section className="rounded-[24px] border border-border bg-white p-6 shadow-sm">
          <SectionHeader
            eyebrow="Coverage overview"
            title="What this snapshot includes"
            description={coverage?.summary ?? 'Ready sources overlapping the selected month range are composed into one cached intelligence view.'}
          />
          {coverage?.notes && coverage.notes.length > 0 ? (
            <ul className="mt-4 space-y-2 text-sm leading-6 text-muted-foreground">
              {coverage.notes.map((note) => (
                <li key={note} className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyInline className="mt-5" title="No coverage notes" description="The snapshot did not include coverage notes for this range." />
          )}
        </section>

        <section className="rounded-[24px] border border-border bg-white p-6 shadow-sm">
          <SectionHeader
            eyebrow="Source cards"
            title="Ready sources in range"
            description="Each card summarizes one source used to build the snapshot."
          />
          {visibleSourceCards.length > 0 ? (
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {visibleSourceCards.map((card) => (
                <PdfInsightCard key={card.sourceId ?? card.title} card={card} />
              ))}
            </div>
          ) : (
            <EmptyInline
              className="mt-5"
              title="No source cards"
              description="The selected range did not return any ready overlapping sources."
            />
          )}
        </section>
      </div>
    </div>
  )
}
