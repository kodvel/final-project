import { ChevronRight, FileSpreadsheet, FileText, Globe } from 'lucide-react'
import { type ReactNode, useEffect, useId, useRef, useState } from 'react'
import type { CitationGroup } from './types'

function CollapsibleContent({ id, open, className, children }: { id: string; open: boolean; className: string; children: ReactNode }) {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = contentRef.current
    if (!element) return

    if (open) {
      element.removeAttribute('inert')
    } else {
      element.setAttribute('inert', '')
    }
  }, [open])

  return (
    <div
      id={id}
      ref={contentRef}
      aria-hidden={!open}
      inert={!open || undefined}
      className={`grid overflow-hidden transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none ${open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}
    >
      <div className={`min-h-0 overflow-hidden ${className}`}>{children}</div>
    </div>
  )
}

export function SourceGroupCard({ group, type }: { group: CitationGroup; type: 'pdf' | 'csv' | 'web' }) {
  const Icon = type === 'pdf' ? FileText : type === 'web' ? Globe : FileSpreadsheet
  const color = type === 'pdf' ? 'text-status-failed-foreground' : type === 'web' ? 'text-primary' : 'text-status-ready-foreground'
  const hasWarning = group.citations.some((citation) => citation.citationStatus !== 'available')
  const [open, setOpen] = useState(false)
  const contentId = useId()

  return (
    <div className={`transition-colors duration-200 ${hasWarning ? 'border-l-2 border-status-failed-foreground/20' : ''}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={contentId}
        className="group flex w-full items-center justify-between gap-3 px-4 py-2 text-left transition-colors duration-200 hover:bg-slate-50 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
      >
        <div className="flex min-w-0 items-center gap-2.5">
          <Icon className={`h-4 w-4 shrink-0 ${color}`} />
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-foreground transition-colors duration-200 group-hover:text-primary">{group.title}</h3>
            <p className="mt-0.5 font-mono text-[11px] text-text-hint">
              {group.citations.length} citation{group.citations.length > 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-chip-gray px-2.5 py-1 font-mono text-[11px] text-text-hint">{group.badge}</span>
          <ChevronRight
            className={`h-4 w-4 shrink-0 text-text-hint transition-transform duration-200 group-hover:text-primary ${open ? 'rotate-90' : ''}`}
          />
        </div>
      </button>

      <CollapsibleContent id={contentId} open={open} className="p-0">
        <div>
          {group.citations.map((citation) => (
            <blockquote
              key={citation.id}
              className="rounded-md border-l border-border/60 bg-transparent pl-3 text-sm italic leading-6 text-muted-foreground"
            >
              "{citation.quote || citation.snippet || (citation.url ? citation.domain || 'Web source' : 'Citation available without quote.')}"
              {citation.url ? (
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 block font-mono text-[11px] not-italic uppercase tracking-[0.12em] text-text-hint transition-colors duration-200 hover:text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
                >
                  [{citation.ordinal ?? citation.id}]{citation.pageNumber != null ? ` p.${citation.pageNumber}` : ''}
                  {citation.domain ? `${citation.domain}` : ''}
                </a>
              ) : (
                <span className="mt-2 block font-mono text-[11px] not-italic uppercase tracking-[0.12em] text-text-hint">
                  [{citation.ordinal ?? citation.id}]{citation.pageNumber != null ? ` p.${citation.pageNumber}` : ''}
                  {citation.domain ? ` · ${citation.domain}` : ''}
                </span>
              )}
            </blockquote>
          ))}
        </div>
      </CollapsibleContent>
    </div>
  )
}
