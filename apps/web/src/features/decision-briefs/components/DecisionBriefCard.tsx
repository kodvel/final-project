import { CheckCircle2, ClipboardList, Lock, ShieldAlert, XCircle } from 'lucide-react'

import type { DecisionApprovalStatus, DecisionBrief, DecisionRecommendationStatus } from '../../../types/decision-brief'
import { useDecisionBrief, useUpdateDecisionBriefStatus } from '../hooks'

type DecisionBriefCardProps = {
  briefId: number
  workspaceId: number
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

export function DecisionBriefCard({ briefId, workspaceId }: DecisionBriefCardProps) {
  const { data: brief, isLoading, error } = useDecisionBrief(briefId, workspaceId)
  const { mutate: updateStatus, isPending } = useUpdateDecisionBriefStatus()

  if (isLoading) {
    return <BriefCardShell>Loading Decision Brief…</BriefCardShell>
  }
  if (error || !brief) {
    return <BriefCardShell>Could not load Decision Brief.</BriefCardShell>
  }

  const content = brief.contentJson
  const locked = brief.approvalStatus === 'approved' || brief.approvalStatus === 'rejected'

  function transitionTo(approvalStatus: DecisionApprovalStatus) {
    if (!brief || isPending) return
    updateStatus({ briefId: brief.id, workspaceId, approvalStatus })
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
        <div className="flex flex-col items-end gap-1.5">
          <RecommendationBadge status={brief.recommendationStatus} />
          <ApprovalBadge status={brief.approvalStatus} />
        </div>
      </header>

      <div className="space-y-4 text-sm leading-7 text-foreground">
        <BriefSection title="Context / Problem" body={content.context_problem} />
        <BriefBulletSection title="Source Evidence" items={content.source_evidence.map((ref) => `[${ref.ordinal}]${ref.note ? ` — ${ref.note}` : ''}`)} />
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
  return (
    <article className="rounded-2xl border border-dashed border-border bg-surface-subtle p-6 text-sm text-muted-foreground">{children}</article>
  )
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

function RecommendationBadge({ status }: { status: DecisionRecommendationStatus }) {
  const Icon = status === 'go' ? CheckCircle2 : status === 'no_go' ? XCircle : ShieldAlert
  const tone =
    status === 'go'
      ? 'border-status-ready/40 bg-status-ready/10 text-status-ready-foreground'
      : status === 'no_go'
        ? 'border-status-failed/40 bg-status-failed/10 text-status-failed-foreground'
        : 'border-status-processing/40 bg-status-processing/10 text-status-processing-foreground'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.12em] ${tone}`}>
      <Icon className="h-3.5 w-3.5" />
      {RECOMMENDATION_LABELS[status]}
    </span>
  )
}

function ApprovalBadge({ status }: { status: DecisionApprovalStatus }) {
  const tone =
    status === 'approved'
      ? 'border-status-ready/40 bg-status-ready/10 text-status-ready-foreground'
      : status === 'rejected'
        ? 'border-status-failed/40 bg-status-failed/10 text-status-failed-foreground'
        : status === 'reviewed'
          ? 'border-primary/40 bg-primary/10 text-primary'
          : 'border-border bg-surface-subtle text-text-hint'
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.12em] ${tone}`}>
      {APPROVAL_LABELS[status]}
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
