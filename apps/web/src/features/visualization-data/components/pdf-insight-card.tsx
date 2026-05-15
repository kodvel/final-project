import { FileText } from 'lucide-react'
import { Badge } from '../../../components/ui/badge'
import type { VisualizationEvidenceRef, VisualizationSourceCard } from '../../../types/visualization'
import { evidenceRefKey, formatLabel } from '../utils'

export function PdfInsightCard({ card }: { card: VisualizationSourceCard }) {
  return (
    <article className="group relative overflow-hidden rounded-2xl border border-border bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="absolute inset-y-0 left-0 w-1.5 bg-primary" />
      <div className="pl-2">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="border-border bg-white text-[11px] text-muted-foreground">
                {card.sourceFileType ?? 'source'}
              </Badge>
              {card.periodLabel && (
                <Badge variant="outline" className="border-border bg-white text-[11px] text-muted-foreground">
                  {card.periodLabel}
                </Badge>
              )}
            </div>
            <h3 className="font-heading text-base font-semibold text-foreground">{card.title}</h3>
          </div>
          <FileText className="h-5 w-5 shrink-0 text-muted-foreground transition group-hover:text-foreground" />
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
          {card.teamLabel && (
            <Badge variant="secondary" className="bg-primary/10 text-primary">
              {formatLabel(card.teamLabel)}
            </Badge>
          )}
          {card.categoryLabels?.map((category) => (
            <Badge key={category} variant="outline" className="border-border bg-white text-muted-foreground">
              {formatLabel(category)}
            </Badge>
          ))}
        </div>

        {card.summary && <p className="mt-4 text-sm leading-6 text-muted-foreground">{card.summary}</p>}

        {card.evidenceRefs && card.evidenceRefs.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {card.evidenceRefs.map((ref) => (
              <EvidenceBadge key={evidenceRefKey(ref)} refItem={ref} />
            ))}
          </div>
        )}

        <div className="mt-4 border-t border-border/70 pt-4">
          <p className="text-xs text-muted-foreground">Source ready for analysis</p>
        </div>
      </div>
    </article>
  )
}

function EvidenceBadge({ refItem }: { refItem: VisualizationEvidenceRef }) {
  const label =
    refItem.quote ?? (refItem.pageNumber != null ? `p.${refItem.pageNumber}` : (refItem.sourceTitle ?? `Source ${refItem.sourceId ?? 'ref'}`))
  return (
    <Badge variant="outline" className="max-w-full border-border bg-white text-[11px] font-normal text-muted-foreground">
      <span className="truncate">{label}</span>
    </Badge>
  )
}
