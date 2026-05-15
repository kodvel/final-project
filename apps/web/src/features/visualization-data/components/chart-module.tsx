import { cn } from '@/lib/utils'
import type { ChartPoint } from '../utils'

export function ChartModule({ series }: { series: ChartPoint[] }) {
  const width = 1000
  const height = 280
  const padding = { top: 18, right: 18, bottom: 42, left: 26 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const maxValue = Math.max(100, ...series.map((point) => Math.max(point.actual, point.baseline)))
  const step = series.length > 0 ? plotWidth / series.length : plotWidth
  const barWidth = Math.min(54, step * 0.42)

  const linePoints = series
    .map((point, index) => {
      const x = padding.left + step * index + step / 2
      const y = padding.top + plotHeight - (point.baseline / maxValue) * plotHeight
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div className={cn('rounded-[22px] border border-border bg-white p-5', series.length === 0 && 'min-h-[280px]')}>
      <div className="mb-4 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <LegendSwatch className="bg-primary" label="Actual signal" />
          <LegendSwatch className="bg-slate-300" label="Projected baseline" dashed />
        </div>
        <p>{series.length} months</p>
      </div>

      {series.length > 0 ? (
        <div className="space-y-4">
          <div className="relative overflow-hidden rounded-2xl border border-border bg-slate-50 px-3 py-4">
            <svg viewBox={`0 0 ${width} ${height}`} className="block h-[280px] w-full" aria-label="Snapshot trajectory chart" role="img">
              {[0, 1, 2, 3].map((row) => (
                <line
                  key={row}
                  x1={padding.left}
                  x2={width - padding.right}
                  y1={padding.top + (plotHeight / 3) * row}
                  y2={padding.top + (plotHeight / 3) * row}
                  stroke="rgba(148, 163, 184, 0.2)"
                  strokeDasharray="6 8"
                />
              ))}

              {series.map((point, index) => {
                const x = padding.left + step * index + step / 2
                const barHeight = (point.actual / maxValue) * plotHeight
                const barX = x - barWidth / 2
                const barY = padding.top + plotHeight - barHeight
                const baselineY = padding.top + plotHeight - (point.baseline / maxValue) * plotHeight
                const tickY = padding.top + plotHeight + 18

                return (
                  <g key={`${point.label}-${Math.round(point.actual)}-${Math.round(point.baseline)}`}>
                    <rect x={barX} y={barY} width={barWidth} height={barHeight} rx="14" fill="#4F46E5" />
                    <rect x={barX} y={barY} width={barWidth} height={barHeight} rx="14" fill="rgba(255,255,255,0.12)" />
                    <circle cx={x} cy={baselineY} r="4.5" fill="#64748B" opacity="0.85" />
                    <text x={x} y={tickY} textAnchor="middle" fontSize="12" fill="#6B7280">
                      {point.label}
                    </text>
                    <title>{`${point.label}: actual ${Math.round(point.actual)}, baseline ${Math.round(point.baseline)}`}</title>
                  </g>
                )
              })}

              <polyline
                points={linePoints}
                fill="none"
                stroke="#64748B"
                strokeWidth="2.5"
                strokeDasharray="8 7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {series.slice(0, 3).map((point) => (
              <div key={`${point.label}-summary`} className="rounded-2xl border border-border bg-slate-50 p-4">
                <p className="text-[11px] font-medium text-muted-foreground">{point.label}</p>
                <p className="mt-2 font-heading text-lg font-semibold text-foreground">{Math.round(point.actual)} signal</p>
                <p className="mt-1 text-sm text-muted-foreground">Baseline {Math.round(point.baseline)}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyInline title="No chart data" description="The selected period did not produce a trajectory yet." />
      )}
    </div>
  )
}

function LegendSwatch({ label, className, dashed }: { label: string; className: string; dashed?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className={cn('h-2.5 w-2.5 rounded-full', className, dashed && 'border border-slate-300 bg-transparent')} />
      {label}
    </span>
  )
}

function EmptyInline({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-white p-5 text-center">
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
    </div>
  )
}
