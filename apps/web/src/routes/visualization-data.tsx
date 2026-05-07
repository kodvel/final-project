import { createFileRoute } from '@tanstack/react-router'
import { ArrowRight, ChevronDown, Download, FileText, Lightbulb, Maximize2, TrendingDown, TrendingUp } from 'lucide-react'
import type { ReactNode } from 'react'
import { useState } from 'react'
import { isChartSpec, isInsightCard } from '../features/visualization-data/api'
import { useInsightCards, useKpiCards, usePrimaryChart, useVisualizationArtifacts } from '../features/visualization-data/hooks'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { CategoryLabel, TeamLabel } from '../types/common'
import type { ChartSpecContent, VisualizationArtifact } from '../types/visualization'

const TEAM_LABELS: TeamLabel[] = ['marketing', 'product', 'data_analysis', 'business']
const CATEGORY_LABELS: CategoryLabel[] = [
  'analytics_metrics',
  'market_research',
  'product_feature',
  'customer_insight',
  'business_model',
  'competitor_analysis',
  'revenue_sales',
]

export const Route = createFileRoute('/visualization-data')({
  component: VisualizationDataPage,
})

function VisualizationDataPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? 0

  const [teamFilter, setTeamFilter] = useState<TeamLabel | ''>('')
  const [categoryFilter, setCategoryFilter] = useState<CategoryLabel | ''>('')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')

  const filters = {
    workspaceId,
    ...(teamFilter && { teamLabel: teamFilter }),
    ...(categoryFilter && { categoryLabel: categoryFilter }),
    ...(periodStart && { periodStart }),
    ...(periodEnd && { periodEnd }),
  }

  const { data: artifacts = [], isLoading, error } = useVisualizationArtifacts(filters)
  const { data: kpis = [] } = useKpiCards(filters)
  const { data: primaryChart } = usePrimaryChart(filters)
  const { data: insights = [] } = useInsightCards(filters)

  // Separate CSV vs PDF artifacts
  const csvArtifacts = artifacts.filter((a) => a.sourceFileType !== 'pdf')
  const pdfArtifacts = artifacts.filter((a) => a.sourceFileType === 'pdf')

  // CSV-only KPIs, chart, and insights
  const csvKpis = kpis.filter((k) => !k.sourceTitle?.endsWith('.pdf'))
  const chartArtifact = primaryChart
  const csvInsights = insights

  if (!activeWorkspace) {
    return (
      <div className="h-full overflow-auto p-8">
        <EmptyState title="Select a Workspace" description="Choose or create a Workspace from the sidebar before viewing Visualizations." />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="h-full overflow-auto p-8">
        <LoadingState />
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full overflow-auto p-8">
        <ErrorState message="Could not load visualizations. Check that the API is running." />
      </div>
    )
  }

  // Show empty state when no ready CSV/PDF artifacts exist
  const hasCsvArtifacts = csvArtifacts.length > 0
  const hasPdfArtifacts = pdfArtifacts.length > 0

  return (
    <div className="h-full overflow-auto p-8 text-foreground">
      <header className="mb-8 flex items-start justify-between gap-6">
        <div>
          <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">AI-Curated Insight Board</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {hasCsvArtifacts || hasPdfArtifacts
              ? 'Synthesized intelligence from connected CSV and PDF data sources.'
              : 'Upload CSV or PDF sources and wait for processing to see insights here.'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <FilterSelect label="Team" value={teamFilter} onChange={setTeamFilter} options={TEAM_LABELS} formatLabel={formatLabel} />
          <FilterSelect label="Category" value={categoryFilter} onChange={setCategoryFilter} options={CATEGORY_LABELS} formatLabel={formatLabel} />
          <PeriodFilter periodStart={periodStart} periodEnd={periodEnd} onStartChange={setPeriodStart} onEndChange={setPeriodEnd} />
        </div>
      </header>

      {!hasCsvArtifacts && !hasPdfArtifacts ? (
        <EmptyState
          title="No Ready Sources"
          description="Upload CSV or PDF sources in Source Data and wait for processing to see visualizations here."
        />
      ) : (
        <>
          {/* KPI cards — only render if we have real CSV KPIs */}
          {csvKpis.length > 0 && (
            <section className="mb-8 grid grid-cols-3 gap-5">
              {csvKpis.slice(0, 3).map((kpi) => (
                <KpiCard
                  key={kpi.label}
                  label={kpi.label}
                  value={kpi.value}
                  delta={kpi.delta ?? ''}
                  trend={kpi.trend ?? 'up'}
                  description=""
                  source={kpi.sourceTitle ?? ''}
                />
              ))}
            </section>
          )}

          {/* Chart section — only render if we have real chart data */}
          {chartArtifact && isChartSpec(chartArtifact.contentJson) && (
            <section className="mb-8 rounded-2xl border border-border bg-background p-6 shadow-sm">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-heading text-lg font-semibold text-foreground">{chartArtifact.contentJson.title || 'Data Visualization'}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{chartArtifact.contentJson.description ?? 'Chart from your data'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <IconButton label="Download">
                    <Download className="h-4 w-4" />
                  </IconButton>
                  <IconButton label="Expand">
                    <Maximize2 className="h-4 w-4" />
                  </IconButton>
                </div>
              </div>

              <ChartSpecChart spec={chartArtifact.contentJson} />

              {chartArtifact.contentJson.insights && chartArtifact.contentJson.insights.length > 0 && (
                <div className="mt-6 flex items-center justify-between rounded-xl border border-accent bg-accent p-4">
                  <div className="flex items-start gap-3">
                    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-background text-primary">
                      <Lightbulb className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">Key Insight</p>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">{chartArtifact.contentJson.insights[0]}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="ml-6 inline-flex shrink-0 items-center gap-2 text-sm font-semibold text-primary hover:text-primary-hover"
                  >
                    Ask in Chat <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </section>
          )}

          {/* Insight cards from CSV sources */}
          {csvInsights.length > 0 && (
            <section className="mb-8 grid grid-cols-2 gap-5">
              {csvInsights.slice(0, 4).map((artifact) => {
                if (!isInsightCard(artifact.contentJson)) return null
                return <InsightCard key={artifact.id} artifact={artifact} />
              })}
            </section>
          )}

          {/* PDF Insight Board — only render if we have PDF artifacts; otherwise show placeholder labeled as mock */}
          {hasPdfArtifacts ? <PdfInsightBoard artifacts={pdfArtifacts} /> : <PdfInsightBoardMock />}
        </>
      )}
    </div>
  )
}

function InsightCard({ artifact }: { artifact: VisualizationArtifact }) {
  if (!isInsightCard(artifact.contentJson)) return null
  const content = artifact.contentJson
  const tone =
    content.insight_type === 'anomaly' || content.insight_type === 'risk'
      ? 'risk'
      : content.insight_type === 'opportunity'
        ? 'opportunity'
        : 'neutral'

  return (
    <article
      className={`rounded-2xl border border-border bg-background p-5 shadow-sm ${tone === 'risk' ? 'border-l-4 border-l-status-failed' : tone === 'opportunity' ? 'border-l-4 border-l-status-ready' : ''}`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
            tone === 'risk'
              ? 'bg-status-failed text-status-failed-foreground'
              : tone === 'opportunity'
                ? 'bg-status-ready text-status-ready-foreground'
                : 'bg-surface-subtle text-muted-foreground'
          }`}
        >
          {content.insight_type}
        </span>
        {artifact.sourceTitle && <span className="font-mono text-[10px] text-text-hint">{artifact.sourceTitle}</span>}
      </div>
      <h3 className="mb-2 font-heading text-base font-semibold text-foreground">{content.title}</h3>
      <p className="text-sm leading-6 text-muted-foreground">{content.description}</p>
      {content.recommendation && <p className="mt-3 text-xs font-semibold text-primary">{content.recommendation}</p>}
    </article>
  )
}

function ChartSpecChart({ spec }: { spec: ChartSpecContent }) {
  const dataPoints = spec.data_points
  const hasData = dataPoints && dataPoints.length > 0 && dataPoints[0].values && dataPoints[0].values.length > 0

  if (!hasData) {
    return (
      <div className="relative h-72 overflow-hidden rounded-xl border border-border bg-surface-subtle flex items-center justify-center">
        <p className="text-sm text-text-hint">Chart visualization will appear here once data is processed.</p>
      </div>
    )
  }

  const bars = dataPoints[0].values.map((value, i) => ({
    label: dataPoints.length > i ? String(dataPoints[i].label) : `M${i + 1}`,
    height: value,
  }))

  return (
    <div className="relative h-72 overflow-hidden rounded-xl border border-border bg-surface-subtle p-6">
      <div className="absolute inset-x-6 top-6 bottom-12 flex flex-col justify-between">
        {['top', 'upper', 'middle', 'lower'].map((line) => (
          <div key={line} className="border-t border-dashed border-border" />
        ))}
      </div>
      <div className="relative z-10 flex h-full items-end gap-4 pb-8">
        {bars.map((bar) => (
          <div key={bar.label} className="flex flex-1 flex-col items-center gap-2">
            <div className="w-full max-w-10 rounded-t-lg bg-gradient-to-t from-primary to-highlight shadow-sm" style={{ height: `${bar.height}%` }} />
            <span className="font-mono text-[10px] text-text-hint">{bar.label}</span>
          </div>
        ))}
      </div>
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-6 bottom-12 h-[calc(100%-72px)] w-[calc(100%-48px)]"
        preserveAspectRatio="none"
        viewBox="0 0 100 100"
      >
        <path
          d="M0 70 C10 64 18 66 27 58 C38 48 45 52 55 42 C66 30 75 37 84 26 C91 18 95 20 100 12"
          fill="none"
          stroke="foreground"
          strokeDasharray="4 4"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  )
}

function PdfInsightBoard({
  artifacts,
}: {
  artifacts: Array<{ id: number; title: string; sourceTitle?: string; contentJson: Record<string, unknown> }>
}) {
  // Group PDF artifacts by source — render first available summary/insight_board
  const firstPdf = artifacts[0]
  const content = firstPdf?.contentJson as Record<string, unknown> | undefined
  const keyFindings = (content?.key_findings as string[]) ?? []
  const risks = (content?.risks as string[]) ?? []
  const opportunities = (content?.opportunities as string[]) ?? []

  return (
    <section className="rounded-2xl border border-border border-l-[3px] border-l-primary bg-background p-6 shadow-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-accent text-primary">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-heading text-lg font-semibold text-foreground">{firstPdf?.title ?? 'PDF Insight Board'}</h2>
            <p className="mt-1 text-sm text-muted-foreground">PDF Insight Board</p>
          </div>
        </div>
        {firstPdf?.sourceTitle && (
          <span className="rounded-full bg-muted px-3 py-1 font-mono text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Source: {firstPdf.sourceTitle}
          </span>
        )}
      </div>

      <div className="grid grid-cols-[1.2fr_1fr] gap-6">
        <div>
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">Key Findings</p>
          {keyFindings.length > 0 ? (
            <ul className="space-y-3 text-sm leading-6 text-foreground">
              {keyFindings.map((finding) => (
                <li key={finding} className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  {finding}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-text-hint">No key findings available.</p>
          )}
        </div>

        <div className="space-y-4">
          {risks.length > 0 && (
            <InsightBox tone="risk" title="Identified Risks">
              {risks.join(' ')}
            </InsightBox>
          )}
          {opportunities.length > 0 && (
            <InsightBox tone="opportunity" title="Opportunities">
              {opportunities.join(' ')}
            </InsightBox>
          )}
          {risks.length === 0 && opportunities.length === 0 && (
            <InsightBox tone="risk" title="Identified Risks">
              Processing complete — insights will appear here once extracted.
            </InsightBox>
          )}
        </div>
      </div>
    </section>
  )
}

function PdfInsightBoardMock() {
  return (
    <section className="rounded-2xl border border-border border-l-[3px] border-l-muted bg-background p-6 shadow-sm opacity-60">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-surface-subtle text-muted-foreground">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-heading text-lg font-semibold text-foreground">PDF Insight Board</h2>
            <p className="mt-1 text-sm text-muted-foreground">No PDF sources processed yet</p>
          </div>
        </div>
        <span className="rounded-full bg-surface-subtle px-3 py-1 font-mono text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          [placeholder]
        </span>
      </div>
      <p className="text-sm text-text-hint">Upload a PDF source and wait for processing to see an insight board here.</p>
    </section>
  )
}

function FilterSelect<T extends string>({
  label,
  value,
  onChange,
  options,
  formatLabel,
}: {
  label: string
  value: T | ''
  onChange: (v: T | '') => void
  options: T[]
  formatLabel: (v: T) => string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange((e.target.value || '') as T | '')}
      className="appearance-none rounded-lg border border-border bg-background px-3 py-2 pr-8 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
    >
      <option value="">{label}</option>
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {formatLabel(opt)}
        </option>
      ))}
    </select>
  )
}

function PeriodFilter({
  periodStart,
  periodEnd,
  onStartChange,
  onEndChange,
}: {
  periodStart: string
  periodEnd: string
  onStartChange: (v: string) => void
  onEndChange: (v: string) => void
}) {
  const hasPeriod = periodStart || periodEnd
  const label = hasPeriod ? `${periodStart || '...'} → ${periodEnd || '...'}` : 'Period'

  return (
    <div className="relative inline-flex items-center gap-1">
      <select
        value=""
        onChange={() => {}}
        className="appearance-none rounded-lg border border-border bg-background px-3 py-2 pr-8 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="">{label}</option>
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 h-4 w-4 text-text-hint" />
      {hasPeriod && (
        <button
          type="button"
          onClick={() => {
            onStartChange('')
            onEndChange('')
          }}
          className="ml-1 text-xs text-muted-foreground hover:text-foreground"
        >
          ×
        </button>
      )}
    </div>
  )
}

function KpiCard({
  label,
  value,
  delta,
  trend,
  description,
  source,
}: {
  label: string
  value: string
  delta: string
  trend: 'up' | 'down'
  description: string
  source: string
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : TrendingDown
  const trendClass = trend === 'up' ? 'text-status-ready-foreground' : 'text-status-failed-foreground'
  const accentClass = trend === 'up' ? 'bg-status-ready' : 'bg-status-failed'
  return (
    <article className="rounded-2xl border border-border bg-background p-5 shadow-sm relative overflow-hidden">
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${accentClass}`} />
      <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <div className="mb-4 flex items-end gap-3">
        <p className="font-heading text-3xl font-semibold tracking-tight text-foreground">{value}</p>
        {delta && (
          <span className={`mb-1 inline-flex items-center gap-1 text-sm font-semibold ${trendClass}`}>
            <TrendIcon className="h-4 w-4" />
            {delta}
          </span>
        )}
      </div>
      <p className="min-h-[48px] pl-2 text-sm leading-6 text-muted-foreground">{description}</p>
      <div className="mt-5 flex items-center justify-between pl-2 border-t border-border-subtle pt-4 text-xs">
        {source && <span className="font-mono text-text-hint">{source}</span>}
        <button type="button" className="font-semibold text-primary hover:text-primary-hover">
          Ask Chat
        </button>
      </div>
    </article>
  )
}

function IconButton({ label, children }: { label: string; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-background text-muted-foreground hover:bg-surface-subtle hover:text-primary"
    >
      {children}
    </button>
  )
}

function InsightBox({ tone, title, children }: { tone: 'risk' | 'opportunity'; title: string; children: ReactNode }) {
  const styles = tone === 'risk' ? 'bg-status-failed text-status-failed-foreground' : 'bg-status-ready text-status-ready-foreground'
  return (
    <div className={`rounded-xl p-4 ${styles}`}>
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.14em]">{title}</p>
      <p className="text-sm leading-6 text-foreground">{children}</p>
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
    <section className="rounded-2xl border border-border bg-background p-8 text-sm text-muted-foreground shadow-sm">
      Loading visualizations...
    </section>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <section className="rounded-2xl border border-status-failed bg-status-failed-light p-8 text-sm text-status-failed shadow-sm">{message}</section>
  )
}

function formatLabel(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}
