import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { VisualizationSnapshotListItem } from '../../../types/visualization'
import { formatConfidence, itemKey, confidenceColorClass } from '../utils'

function ConfidenceInline({ value }: { value: string }) {
  const colorClass = confidenceColorClass(value)
  if (colorClass) {
    return (
      <span className={`mt-1 inline-block rounded border px-1.5 py-0.5 text-[11px] font-semibold uppercase ${colorClass}`}>
        {value.toUpperCase()}
      </span>
    )
  }
  return <p className="mt-1 text-xs text-muted-foreground">{value}</p>
}

export function InsightMiniCard({
  title,
  icon,
  items,
  tone,
  emptyTitle,
}: {
  title: string
  icon: ReactNode
  items: VisualizationSnapshotListItem[]
  tone: 'indigo' | 'emerald' | 'amber' | 'rose'
  emptyTitle: string
}) {
  const toneClass = {
    indigo: 'border-indigo-100 bg-indigo-50/60 text-indigo-700',
    emerald: 'border-emerald-100 bg-emerald-50/60 text-emerald-700',
    amber: 'border-amber-100 bg-amber-50/60 text-amber-700',
    rose: 'border-rose-100 bg-rose-50/60 text-rose-700',
  }[tone]

  return (
    <article className="rounded-2xl border border-border bg-white p-4 transition hover:-translate-y-0.5 hover:shadow-sm">
      <div className="flex items-center gap-2">
        <div className={cn('rounded-full border p-2', toneClass)}>{icon}</div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">{title}</p>
        </div>
      </div>

      {items.length > 0 ? (
        <div className="mt-4 space-y-2">
          {items.slice(0, 3).map((item) => (
            <div key={itemKey(item)} className="rounded-xl border border-border bg-surface-subtle px-3 py-2.5">
              <p className="text-sm text-muted-foreground leading-6">{item.title ?? item.text ?? item.detail ?? item.description ?? 'Untitled item'}</p>
              {item.confidence != null && (
                <ConfidenceInline value={formatConfidence(item.confidence)} />
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">{emptyTitle}</div>
      )}
    </article>
  )
}
