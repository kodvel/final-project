import { FileSpreadsheet, FileText, Globe } from 'lucide-react'
import type { MessageSourceCitation } from '../../../types/chat'

export function EvidenceChip({ citation }: { citation: MessageSourceCitation }) {
  const isWeb = citation.citationType === 'web'
  const Icon = isWeb ? Globe : citation.title?.toLowerCase().endsWith('.pdf') ? FileText : FileSpreadsheet
  const color = isWeb ? 'text-primary' : 'text-status-ready-foreground'
  const label = isWeb ? citation.domain || citation.title || 'Web Source' : citation.title || `Source #${citation.sourceId ?? 'unknown'}`
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card px-3 py-2 font-mono text-xs text-foreground transition hover:border-primary/20 hover:bg-surface-subtle"
      title={citation.quote ?? citation.url ?? undefined}
    >
      <Icon className={`h-4 w-4 ${color}`} />[{citation.ordinal ?? citation.id}] {label}
      {citation.citationStatus !== 'available' && <span className="text-status-failed-foreground">warning</span>}
    </span>
  )
}
