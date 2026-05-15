import { Badge } from '../../../components/ui/badge'

export function KpiCard({ label, value, detail, accent }: { label: string; value: string; detail: string; accent: 'indigo' | 'emerald' | 'amber' }) {
  const accentClass = {
    indigo: 'bg-primary',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
  }[accent]

  return (
    <article className="group relative overflow-hidden rounded-[24px] border border-border bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className={`absolute inset-y-0 left-0 w-1.5 ${accentClass}`} />
      <div className="pl-2">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <div className="mt-3 flex items-end justify-between gap-4">
          <p className="font-heading text-3xl font-semibold tracking-tight text-foreground">{value}</p>
          <Badge variant="outline" className="border-border bg-surface-subtle text-[11px] text-muted-foreground">
            Snapshot
          </Badge>
        </div>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{detail}</p>
      </div>
    </article>
  )
}
