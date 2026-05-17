import { FileSpreadsheet, FileText, Globe } from 'lucide-react'
import type { MessageSourceCitation } from '../../../types/chat'

export function EvidenceChip({ citation }: { citation: MessageSourceCitation }) {
  const isWeb = citation.citationType === 'web'
  const Icon = isWeb ? Globe : citation.title?.toLowerCase().endsWith('.pdf') ? FileText : FileSpreadsheet
  const color = isWeb ? 'text-primary' : 'text-status-ready-foreground'
  const label = isWeb ? citation.domain || citation.title || 'Web Source' : citation.title || `Source #${citation.sourceId ?? 'unknown'}`
  const chipContent = (
    <>
      <Icon className={`h-4 w-4 ${color}`} />[{citation.ordinal ?? citation.id}] {label}
      {citation.citationStatus !== 'available' && <span className="text-status-failed-foreground">warning</span>}
    </>
  )

  if (citation.url) {
    return (
      <a
        href={citation.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card px-3 py-2 font-mono text-xs text-foreground no-underline transition hover:border-primary/20 hover:bg-surface-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
        title={citation.quote ?? citation.url}
      >
        {chipContent}
      </a>
    )
  }

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card px-3 py-2 font-mono text-xs text-foreground transition hover:border-primary/20 hover:bg-surface-subtle"
      title={citation.quote ?? undefined}
    >
      {chipContent}
    </span>
  )
}
