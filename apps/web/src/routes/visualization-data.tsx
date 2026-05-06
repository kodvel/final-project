import { createFileRoute } from '@tanstack/react-router'
import { ArrowRight, ChevronDown, Download, FileText, Lightbulb, Maximize2, TrendingDown, TrendingUp } from 'lucide-react'
import type { ReactNode } from 'react'

export const Route = createFileRoute('/visualization-data')({
  component: VisualizationDataPage,
})

function VisualizationDataPage() {
  return (
    <div className="h-full overflow-auto p-8 text-foreground">
      <header className="mb-8 flex items-start justify-between gap-6">
        <div>
          <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">AI-Curated Insight Board</h1>
          <p className="mt-1 text-sm text-muted-foreground">Synthesized intelligence from connected CSV and PDF data sources.</p>
        </div>
        <div className="flex items-center gap-3">
          <FilterButton label="Team: Executive" />
          <FilterButton label="Category" />
          <FilterButton label="Period: YTD 2023" />
        </div>
      </header>

      <section className="mb-8 grid grid-cols-3 gap-5">
        <KpiCard
          label="Total Revenue"
          value="$42.8M"
          delta="+12.4%"
          trend="up"
          description="Enterprise expansion and net-new logo growth lifted revenue above the projected baseline."
          source="Q3_Revenue.csv"
        />
        <KpiCard
          label="Operating Margin"
          value="24.2%"
          delta="-1.1%"
          trend="down"
          description="Margin compressed as implementation and enablement spend increased for larger accounts."
          source="Finance_Model.csv"
        />
        <KpiCard
          label="Net Retention"
          value="118%"
          delta="+3.0%"
          trend="up"
          description="Expansion revenue offset onboarding friction, but renewal quality remains uneven."
          source="CRM_Pipeline.csv"
        />
      </section>

      <section className="mb-8 rounded-2xl border border-border bg-background p-6 shadow-sm">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="font-heading text-lg font-semibold text-foreground">Revenue Growth Trajectory</h2>
            <p className="mt-1 text-sm text-muted-foreground">Monthly actuals vs projected baseline</p>
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

        <MockChart />

        <div className="mt-6 flex items-center justify-between rounded-xl border border-accent bg-accent p-4">
          <div className="flex items-start gap-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-background text-primary">
              <Lightbulb className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">Key Insight</p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Revenue growth accelerated in Q3, driven by enterprise segment expansion, but onboarding complexity remains the main retention risk.
              </p>
            </div>
          </div>
          <button type="button" className="ml-6 inline-flex shrink-0 items-center gap-2 text-sm font-semibold text-primary hover:text-primary-hover">
            Ask in Chat <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-border border-l-[3px] border-l-primary bg-background p-6 shadow-sm">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-accent text-primary">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-semibold text-foreground">Strategic Analysis Summary</h2>
              <p className="mt-1 text-sm text-muted-foreground">PDF Insight Board</p>
            </div>
          </div>
          <span className="rounded-full bg-muted px-3 py-1 font-mono text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Source: Strategic_Analysis.pdf
          </span>
        </div>

        <div className="grid grid-cols-[1.2fr_1fr] gap-6">
          <div>
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">Key Findings</p>
            <ul className="space-y-3 text-sm leading-6 text-foreground">
              <li className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Enterprise demand is growing fastest where onboarding support is bundled with rollout planning.
              </li>
              <li className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Renewal risk clusters around legacy workflows affected by the new interface.
              </li>
              <li className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Decision quality improves when product, revenue, and support Sources are reviewed together.
              </li>
            </ul>
          </div>

          <div className="space-y-4">
            <InsightBox tone="risk" title="Identified Risks">
              Longer onboarding cycles could reduce enterprise renewal confidence if enablement remains reactive.
            </InsightBox>
            <InsightBox tone="opportunity" title="Opportunities">
              Package a guided transition playbook for enterprise accounts before Q3 renewal conversations begin.
            </InsightBox>
          </div>
        </div>
      </section>
    </div>
  )
}

function FilterButton({ label }: { label: string }) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-surface-subtle"
    >
      {label}
      <ChevronDown className="h-4 w-4 text-text-hint" />
    </button>
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
  return (
    <article className="rounded-2xl border border-border bg-background p-5 shadow-sm">
      <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <div className="mb-4 flex items-end gap-3">
        <p className="font-heading text-3xl font-semibold tracking-tight text-foreground">{value}</p>
        <span className={`mb-1 inline-flex items-center gap-1 text-sm font-semibold ${trendClass}`}>
          <TrendIcon className="h-4 w-4" />
          {delta}
        </span>
      </div>
      <p className="min-h-[48px] text-sm leading-6 text-muted-foreground">{description}</p>
      <div className="mt-5 flex items-center justify-between text-xs">
        <span className="font-mono text-text-hint">{source}</span>
        <button type="button" className="font-semibold text-primary hover:text-primary-hover">
          Ask Chat
        </button>
      </div>
    </article>
  )
}

function MockChart() {
  const bars = [
    { label: 'M1', height: 42 },
    { label: 'M2', height: 48 },
    { label: 'M3', height: 44 },
    { label: 'M4', height: 58 },
    { label: 'M5', height: 62 },
    { label: 'M6', height: 72 },
    { label: 'M7', height: 68 },
    { label: 'M8', height: 76 },
    { label: 'M9', height: 84 },
    { label: 'M10', height: 92 },
    { label: 'M11', height: 88 },
    { label: 'M12', height: 98 },
  ]
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
