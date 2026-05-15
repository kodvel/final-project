import { cn } from '@/lib/utils'
import type { ChartPoint } from '../utils'

export function ChartModule({ series }: { series: ChartPoint[] }) {
  const width = 1000
  const height = 300
  const padding = { top: 24, right: 24, bottom: 44, left: 28 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const maxValue = Math.max(100, ...series.map((point) => Math.max(point.actual, point.baseline)))
  const step = series.length > 0 ? plotWidth / series.length : plotWidth
  const barWidth = Math.min(56, step * 0.44)

  const linePoints = series
    .map((point, index) => {
      const x = padding.left + step * index + step / 2
      const y = padding.top + plotHeight - (point.baseline / maxValue) * plotHeight
      return `${x},${y}`
    })
    .join(' ')

  const hasBaseline = series.some((p) => p.baseline > 0)

  return (
    <div className={cn('rounded-[22px] border border-border bg-white', series.length === 0 && 'min-h-[280px]')}>
      {series.length > 0 && (
        <div className="mb-3 flex items-center justify-between gap-3 px-4 pt-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-indigo-500" />
              Actual
            </span>
            {hasBaseline && (
              <span className="inline-flex items-center gap-1.5">
                <span className="h-0 w-4 border-t-2 border-dashed border-slate-400" />
                Projected
              </span>
            )}
          </div>
          <p className="tabular-nums">{series.length} months</p>
        </div>
      )}

      {series.length > 0 ? (
        <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-b from-slate-50/80 to-white px-3 pb-4 pt-2">
          <svg viewBox={`0 0 ${width} ${height}`} className="block h-[300px] w-full" aria-label="Snapshot trajectory chart" role="img">
            {/* Grid lines */}
            {[0, 1, 2, 3].map((row) => (
              <line
                key={row}
                x1={padding.left}
                x2={width - padding.right}
                y1={padding.top + (plotHeight / 3) * row}
                y2={padding.top + (plotHeight / 3) * row}
                stroke="rgba(148, 163, 184, 0.15)"
                strokeWidth="1"
              />
            ))}

            {/* Baseline polyline (rendered behind bars) */}
            {hasBaseline && (
              <polyline
                points={linePoints}
                fill="none"
                stroke="#94A3B8"
                strokeWidth="2"
                strokeDasharray="8 6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Bars + baseline dots + labels */}
            {series.map((point, index) => {
              const x = padding.left + step * index + step / 2
              const barHeight = (point.actual / maxValue) * plotHeight
              const barX = x - barWidth / 2
              const barY = padding.top + plotHeight - barHeight
              const baselineY = padding.top + plotHeight - (point.baseline / maxValue) * plotHeight
              const tickY = padding.top + plotHeight + 22

              return (
                <g key={`${point.label}-${Math.round(point.actual)}-${Math.round(point.baseline)}`}>
                  {/* Bar shadow */}
                  <rect x={barX + 2} y={barY + 2} width={barWidth} height={barHeight} rx="10" fill="rgba(79,70,229,0.06)" />
                  {/* Bar fill */}
                  <rect x={barX} y={barY} width={barWidth} height={barHeight} rx="10" fill="#4F46E5" />
                  {/* Subtle highlight on bar */}
                  <rect x={barX} y={barY} width={barWidth * 0.4} height={barHeight} rx="10" fill="rgba(255,255,255,0.10)" />
                  {/* Baseline dot */}
                  {hasBaseline && <circle cx={x} cy={baselineY} r="4" fill="#64748B" opacity="0.7" />}
                  {/* X-axis label */}
                  <text x={x} y={tickY} textAnchor="middle" fontSize="11.5" fill="#94A3B8" fontFamily="system-ui, sans-serif">
                    {point.label}
                  </text>
                  <title>{`${point.label}: ${Math.round(point.actual)}`}</title>
                </g>
              )
            })}
          </svg>
        </div>
      ) : (
        <div className="px-5 pb-5 pt-3">
          <EmptyInline title="No chart data" description="The selected period did not produce a trajectory yet." />
        </div>
      )}
    </div>
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
