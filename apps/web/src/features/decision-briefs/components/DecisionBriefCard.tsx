import { CheckCircle2, ClipboardCheck, ClipboardList, Eye, FilePen, FileSpreadsheet, FileText, Globe, Lock, ShieldAlert, XCircle } from 'lucide-react'

import { useChatSession } from '../../chat/hooks'
import type { MessageSourceCitation } from '../../../types/chat'
import type { DecisionApprovalStatus, DecisionRecommendationStatus } from '../../../types/decision-brief'
import { useDecisionBrief, useUpdateDecisionBriefStatus } from '../hooks'

type DecisionBriefCardProps = {
  briefId: number
  workspaceId: number
  onActionComplete?: () => void
}

const RECOMMENDATION_LABELS: Record<DecisionRecommendationStatus, string> = {
  go: 'Go',
  no_go: 'No-Go',
  validate_first: 'Validate First',
}

const APPROVAL_LABELS: Record<DecisionApprovalStatus, string> = {
  draft: 'Draft',
  reviewed: 'Reviewed',
  approved: 'Approved',
  rejected: 'Rejected',
}

export function DecisionBriefCard({ briefId, workspaceId, onActionComplete }: DecisionBriefCardProps) {
  const { data: brief, isLoading, error } = useDecisionBrief(briefId, workspaceId)
  const { mutate: updateStatus, isPending } = useUpdateDecisionBriefStatus()
  const { data: session } = useChatSession(brief?.chatSessionId ?? null, workspaceId)

  if (isLoading) {
    return <BriefCardShell>Loading Decision Brief…</BriefCardShell>
  }
  if (error || !brief) {
    return <BriefCardShell>Could not load Decision Brief.</BriefCardShell>
  }

  const content = brief.contentJson
  const locked = brief.approvalStatus === 'approved' || brief.approvalStatus === 'rejected'

  // Resolve each source_evidence ordinal to its actual citation from the
  // originating chat session.
  const citationByOrdinal = new Map<number, MessageSourceCitation>()
  for (const citation of session?.citations ?? []) {
    if (citation.ordinal != null && !citationByOrdinal.has(citation.ordinal)) {
      citationByOrdinal.set(citation.ordinal, citation)
    }
  }

  function transitionTo(approvalStatus: DecisionApprovalStatus) {
    if (!brief || isPending) return
    updateStatus(
      { briefId: brief.id, workspaceId, approvalStatus },
      { onSuccess: () => onActionComplete?.() },
    )
  }

  return (
    <article className="rounded-2xl border border-border bg-card p-6 shadow-sm space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-text-hint">
            <ClipboardList className="h-3.5 w-3.5" />
            Decision Brief #{brief.sequenceNumber}
          </div>
          <h3 className="font-heading text-lg font-semibold text-foreground">{brief.title}</h3>
          {brief.objective && <p className="text-sm leading-6 text-muted-foreground">{brief.objective}</p>}
        </div>
        <div className="flex flex-wrap items-start gap-x-5 gap-y-2">
          <BadgeWithLabel label="Recommendation">
            <RecommendationBadge status={brief.recommendationStatus} />
          </BadgeWithLabel>
          <BadgeWithLabel label="Approval">
            <ApprovalBadge status={brief.approvalStatus} />
          </BadgeWithLabel>
        </div>
      </header>

      <div className="space-y-4 text-sm leading-7 text-foreground">
        <BriefSection title="Context / Problem" body={content.context_problem} />
        <EvidenceSection refs={content.source_evidence} citationByOrdinal={citationByOrdinal} />
        <BriefSection title="Strategic Interpretation" body={content.strategic_interpretation} />
        <BriefSection title="Recommendation" body={content.recommendation} />
        <BriefBulletSection title="Alternatives Considered" items={content.alternatives_considered} />
        <BriefBulletSection title="Risks & Assumptions" items={content.risks_assumptions} />
        <BriefBulletSection title="Success Metrics" items={content.success_metrics} />
        <BriefBulletSection title="Next Steps" items={content.next_steps} />
      </div>

      <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-border pt-4">
        {locked ? (
          <span className="inline-flex items-center gap-2 text-xs font-medium text-text-hint">
            <Lock className="h-3.5 w-3.5" /> Locked — {APPROVAL_LABELS[brief.approvalStatus]}
          </span>
        ) : (
          <>
            {brief.approvalStatus === 'draft' && (
              <StatusButton onClick={() => transitionTo('reviewed')} disabled={isPending}>
                Mark Reviewed
              </StatusButton>
            )}
            <StatusButton onClick={() => transitionTo('approved')} disabled={isPending} tone="primary">
              Approve
            </StatusButton>
            <StatusButton onClick={() => transitionTo('rejected')} disabled={isPending} tone="danger">
              Reject
            </StatusButton>
          </>
        )}
      </footer>
    </article>
  )
}

function BriefCardShell({ children }: { children: React.ReactNode }) {
  return <article className="rounded-2xl border border-dashed border-border bg-surface-subtle p-6 text-sm text-muted-foreground">{children}</article>
}

function BriefSection({ title, body }: { title: string; body: string | undefined }) {
  if (!body) return null
  return (
    <div className="space-y-1">
      <h4 className="font-mono text-[11px] uppercase tracking-[0.18em] text-text-hint">{title}</h4>
      <p className="whitespace-pre-line text-[15px] leading-7 text-foreground">{body}</p>
    </div>
  )
}

function EvidenceSection({
  refs,
  citationByOrdinal,
}: {
  refs: { ordinal: number; note?: string | null }[]
  citationByOrdinal: Map<number, MessageSourceCitation>
}) {
  if (!refs || refs.length === 0) return null
  return (
    <div className="space-y-1.5">
      <h4 className="font-mono text-[11px] uppercase tracking-[0.18em] text-text-hint">Source Evidence</h4>
      <ul className="space-y-2">
        {refs.map((ref, idx) => {
          const citation = citationByOrdinal.get(ref.ordinal)
          return (
            <li key={`${ref.ordinal}-${idx}`} className="rounded-lg border border-border/60 bg-surface-subtle/50 p-3">
              <EvidenceRefRow ordinal={ref.ordinal} note={ref.note ?? null} citation={citation} />
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function EvidenceRefRow({
  ordinal,
  note,
  citation,
}: {
  ordinal: number
  note: string | null
  citation: MessageSourceCitation | undefined
}) {
  if (!citation) {
    return (
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-chip-gray px-1.5 py-0.5 font-mono text-[11px] text-text-hint">[{ordinal}]</span>
          <span className="text-xs text-text-hint italic">Citation not found in this session.</span>
        </div>
        {note && <p className="pl-2 text-xs leading-5 text-muted-foreground">{note}</p>}
      </div>
    )
  }

  const isWeb = citation.citationType === 'web'
  const isPdf = !isWeb && (citation.title?.toLowerCase().endsWith('.pdf') ?? false)
  const Icon = isWeb ? Globe : isPdf ? FileText : FileSpreadsheet
  const iconTone = isWeb ? 'text-primary' : isPdf ? 'text-status-failed-foreground' : 'text-status-ready-foreground'
  const title = isWeb
    ? citation.title || citation.domain || 'Web Source'
    : citation.title || `Source #${citation.sourceId ?? 'unknown'}`
  const quote = citation.quote || citation.snippet

  const ordinalBadge = citation.url ? (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="rounded-md bg-chip-gray px-1.5 py-0.5 font-mono text-[11px] text-text-hint no-underline transition-colors duration-200 hover:bg-primary/10 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
      title={citation.url}
    >
      [{ordinal}]
    </a>
  ) : (
    <span className="rounded-md bg-chip-gray px-1.5 py-0.5 font-mono text-[11px] text-text-hint">[{ordinal}]</span>
  )

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        {ordinalBadge}
        <Icon className={`h-3.5 w-3.5 shrink-0 ${iconTone}`} />
        <span className="truncate text-xs font-semibold text-foreground">{title}</span>
        {citation.pageNumber != null && (
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-text-hint">p.{citation.pageNumber}</span>
        )}
      </div>
      {quote && <blockquote className="border-l border-border/60 pl-3 text-xs italic leading-5 text-muted-foreground">"{quote}"</blockquote>}
      {note && <p className="text-xs leading-5 text-muted-foreground">{note}</p>}
    </div>
  )
}

function BriefBulletSection({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null
  return (
    <div className="space-y-1">
      <h4 className="font-mono text-[11px] uppercase tracking-[0.18em] text-text-hint">{title}</h4>
      <ul className="list-disc space-y-1 pl-5 text-[15px] leading-7 text-foreground">
        {items.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

function BadgeWithLabel({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-1">
      <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-hint">{label}</span>
      {children}
    </div>
  )
}

// Shared shape so the two badges line up regardless of label length and visual style.
const BADGE_BASE = 'inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs font-semibold tracking-wide'

function RecommendationBadge({ status }: { status: DecisionRecommendationStatus }) {
  const Icon = status === 'go' ? CheckCircle2 : status === 'no_go' ? XCircle : ShieldAlert
  // Solid filled — recommendation is the headline outcome.
  const tone =
    status === 'go'
      ? 'border-status-ready bg-status-ready text-status-ready-foreground shadow-sm'
      : status === 'no_go'
        ? 'border-status-failed bg-status-failed text-status-failed-foreground shadow-sm'
        : 'border-status-processing bg-status-processing text-status-processing-foreground shadow-sm'
  return (
    <span className={`${BADGE_BASE} ${tone}`}>
      <Icon className="h-3.5 w-3.5" />
      {RECOMMENDATION_LABELS[status]}
    </span>
  )
}

function ApprovalBadge({ status }: { status: DecisionApprovalStatus }) {
  // Outlined — secondary visual weight against the recommendation.
  const Icon =
    status === 'approved'
      ? ClipboardCheck
      : status === 'rejected'
        ? XCircle
        : status === 'reviewed'
          ? Eye
          : FilePen
  const tone =
    status === 'approved'
      ? 'border-status-ready/50 bg-status-ready/10 text-status-ready-foreground'
      : status === 'rejected'
        ? 'border-status-failed/50 bg-status-failed/10 text-status-failed-foreground'
        : status === 'reviewed'
          ? 'border-primary/50 bg-primary/10 text-primary'
          : 'border-border bg-surface-subtle text-text-hint'
  const showLockHint = status === 'approved' || status === 'rejected'
  return (
    <span className={`${BADGE_BASE} ${tone}`}>
      <Icon className="h-3.5 w-3.5" />
      {APPROVAL_LABELS[status]}
      {showLockHint && <Lock className="h-3 w-3 opacity-70" />}
    </span>
  )
}

function StatusButton({
  children,
  onClick,
  disabled,
  tone,
}: {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  tone?: 'primary' | 'danger'
}) {
  const base = 'rounded-lg border px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50'
  const palette =
    tone === 'primary'
      ? 'border-primary bg-primary text-primary-foreground hover:bg-primary/90'
      : tone === 'danger'
        ? 'border-status-failed/40 text-status-failed-foreground hover:bg-status-failed/10'
        : 'border-border text-foreground hover:bg-surface-subtle'
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${base} ${palette}`}>
      {children}
    </button>
  )
}
