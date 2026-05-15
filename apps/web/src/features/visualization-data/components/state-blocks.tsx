import { cn } from '@/lib/utils'
import { Badge } from '../../../components/ui/badge'

export function EmptyInline({ title, description, className }: { title: string; description: string; className?: string }) {
  return (
    <div className={cn('rounded-2xl border border-dashed border-border bg-white p-5 text-center', className)}>
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-border bg-white p-10 text-center shadow-sm">
      <h3 className="font-heading text-lg font-semibold text-foreground">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
    </section>
  )
}

export function LoadingState() {
  return (
    <section className="space-y-4 p-8">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
        <div>
          <p className="font-medium text-foreground">Preparing visualizations</p>
          <p className="mt-1 text-xs text-muted-foreground">Analyzing data and building charts...</p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
        <div className="h-32 animate-pulse rounded-2xl bg-muted" />
      </div>
    </section>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <section className="rounded-2xl border border-status-failed bg-status-failed-light p-8 text-sm text-status-failed shadow-sm">{message}</section>
  )
}

export function SnapshotStatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  const styles = normalized.includes('ready')
    ? 'border-emerald-100 bg-emerald-50 text-emerald-700'
    : normalized.includes('process')
      ? 'border-amber-100 bg-amber-50 text-amber-700'
      : normalized.includes('fail')
        ? 'border-rose-100 bg-rose-50 text-rose-700'
        : 'border-sky-100 bg-sky-50 text-sky-700'

  return (
    <Badge variant="outline" className={cn('border text-[11px]', styles)}>
      {status}
    </Badge>
  )
}
