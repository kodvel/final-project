import { Eye, FileSpreadsheet, FileText } from 'lucide-react'
import type { CitationGroup } from './types'

export function SourceGroupCard({ group, type }: { group: CitationGroup; type: 'pdf' | 'csv' | 'web' }) {
  const firstCitation = group.citations[0]
  const Icon = type === 'pdf' ? FileText : type === 'web' ? Eye : FileSpreadsheet
  const color = type === 'pdf' ? 'text-status-failed-foreground' : type === 'web' ? 'text-primary' : 'text-status-ready-foreground'
  const hasWarning = group.citations.some((citation) => citation.citationStatus !== 'available')

  return (
    <details className={`rounded-xl border bg-card p-5 shadow-sm ${hasWarning ? 'border-status-failed-foreground/40' : 'border-border'}`}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className={`h-4 w-4 shrink-0 ${color}`} />
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-foreground">{group.title}</h3>
            <p className="mt-1 font-mono text-[11px] text-text-hint">
              {group.citations.length} citation{group.citations.length > 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <span className="rounded bg-chip-gray px-2 py-1 font-mono text-[11px] text-text-hint">{group.badge}</span>
      </summary>
      <div className="mt-4 space-y-3">
        {group.citations.map((citation) => (
          <blockquote key={citation.id} className="border-l-2 border-border pl-4 text-sm italic leading-6 text-muted-foreground">
            "{citation.quote || citation.snippet || citation.url || 'Citation available without quote.'}"
            <span className="mt-2 block text-xs not-italic text-text-hint">
              [{citation.ordinal ?? citation.id}]{citation.pageNumber != null ? ` p.${citation.pageNumber}` : ''}
              {citation.domain ? ` · ${citation.domain}` : ''}
            </span>
          </blockquote>
        ))}
        {firstCitation?.url && (
          <a
            href={firstCitation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block truncate font-mono text-xs text-primary hover:underline"
          >
            {firstCitation.url}
          </a>
        )}
      </div>
    </details>
  )
}
