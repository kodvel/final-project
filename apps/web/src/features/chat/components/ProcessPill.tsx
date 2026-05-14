import { Workflow } from 'lucide-react'

export function ProcessPill({ label, status }: { label: string; status: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-subtle px-3 py-1 font-mono text-[11px] text-text-hint">
      <Workflow className="h-3.5 w-3.5" />
      {label}
      <span className={status === 'failed' ? 'text-status-failed-foreground' : status === 'done' ? 'text-status-ready-foreground' : 'text-text-hint'}>
        {status === 'running' ? 'running' : status}
      </span>
    </span>
  )
}
