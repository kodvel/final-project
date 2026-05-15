import { createFileRoute } from '@tanstack/react-router'
import { CheckCircle2, ChevronLeft, ChevronRight, ClipboardList, Search, ShieldAlert, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { useMemo, useState } from 'react'

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog'
import { DecisionBriefCard } from '../features/decision-briefs/components/DecisionBriefCard'
import { useDecisionBriefs } from '../features/decision-briefs/hooks'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { DecisionApprovalStatus, DecisionBrief, DecisionRecommendationStatus } from '../types/decision-brief'

export const Route = createFileRoute('/decision-briefs')({
  component: DecisionBriefsPage,
})

const APPROVAL_OPTIONS: ReadonlyArray<{ value: DecisionApprovalStatus; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
]

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

function DecisionBriefsPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? null

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [openBriefId, setOpenBriefId] = useState<number | null>(null)

  const { data: briefs = [], isLoading, error } = useDecisionBriefs(workspaceId)

  const filteredBriefs = useMemo(() => {
    const term = search.trim().toLowerCase()
    return briefs.filter((brief) => {
      if (term && !brief.title.toLowerCase().includes(term)) return false
      if (statusFilter && brief.approvalStatus !== statusFilter) return false
      return true
    })
  }, [briefs, search, statusFilter])

  function clearFilters() {
    setSearch('')
    setStatusFilter('')
  }

  // Workspace-level stats stay unchanged by filters
  const totalBriefs = briefs.length
  const approvedCount = briefs.filter((b) => b.approvalStatus === 'approved').length
  const pendingCount = briefs.filter((b) => b.approvalStatus === 'draft' || b.approvalStatus === 'reviewed').length
  const rejectedCount = briefs.filter((b) => b.approvalStatus === 'rejected').length

  const hasActiveFilter = Boolean(search || statusFilter)

  return (
    <div className="h-full overflow-auto p-8">
      {!activeWorkspace ? (
        <EmptyState
          title="Select a Workspace"
          description="Choose or create a Workspace from the bottom-left switcher to view Decision Briefs."
        />
      ) : isLoading ? (
        <Panel>Loading Decision Briefs...</Panel>
      ) : error ? (
        <Panel>Could not load Decision Briefs. Check that the API is running.</Panel>
      ) : (
        <>
          {/* Header row */}
          <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">Decision Briefs</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                All decisions produced in this Workspace. Approved Briefs are reachable across Chat Sessions.
              </p>
            </div>
          </div>

          {/* Stats cards row */}
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard number={totalBriefs.toLocaleString()} label="Total Briefs" accent="" />
            <StatCard number={approvedCount.toLocaleString()} label="Approved" accent="blue" />
            <StatCard number={pendingCount.toLocaleString()} label="Pending" accent="amber" />
            <StatCard number={rejectedCount.toLocaleString()} label="Rejected" accent="red" />
          </div>

          {/* Filter bar */}
          <div className="mb-4 flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-hint" />
              <input
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by title..."
                className="w-full rounded-lg border border-border bg-background py-2 pl-10 pr-4 text-sm text-foreground placeholder-text-hint focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <FilterDropdown label="All Statuses" value={statusFilter} onChange={setStatusFilter} options={APPROVAL_OPTIONS} />
            {hasActiveFilter && (
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-muted-foreground transition hover:bg-surface-subtle hover:text-foreground"
              >
                Clear
              </button>
            )}
          </div>

          {/* Table */}
          {briefs.length === 0 ? (
            <EmptyState
              title="No Decision Briefs yet"
              description="Run /decision-brief in Chat to produce your first Decision Brief Draft for this Workspace."
            />
          ) : (
            <BriefTable briefs={filteredBriefs} onOpen={setOpenBriefId} />
          )}

          {/* Pagination */}
          {briefs.length > 0 && (
            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Showing {filteredBriefs.length} of {briefs.length} brief{briefs.length === 1 ? '' : 's'}
                {hasActiveFilter ? ' (filtered)' : ''}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 transition hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-50"
                  disabled
                >
                  <ChevronLeft className="h-4 w-4" />
                  Prev
                </button>
                <button
                  type="button"
                  className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 transition hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-50"
                  disabled
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {openBriefId !== null && workspaceId && (
        <Dialog open onOpenChange={(open) => !open && setOpenBriefId(null)}>
          <DialogContent className="flex max-h-[85vh] max-w-3xl flex-col gap-0 rounded-2xl p-0 sm:max-w-3xl">
            <DialogHeader className="shrink-0 border-b border-border px-6 py-4">
              <DialogTitle className="font-heading text-lg">Decision Brief</DialogTitle>
              <DialogDescription>Review the Brief and update its approval status.</DialogDescription>
            </DialogHeader>
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
              <DecisionBriefCard
                briefId={openBriefId}
                workspaceId={workspaceId}
                onActionComplete={() => setOpenBriefId(null)}
              />
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}

function BriefTable({ briefs, onOpen }: { briefs: DecisionBrief[]; onOpen: (briefId: number) => void }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-background shadow-sm">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3">#</th>
            <th className="px-4 py-3">Title</th>
            <th className="px-4 py-3">Recommendation</th>
            <th className="px-4 py-3">Approval</th>
            <th className="px-4 py-3">Generated</th>
            <th className="px-4 py-3">Origin</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {briefs.length === 0 ? (
            <tr>
              <td colSpan={7} className="px-4 py-8 text-center text-text-hint">
                No Decision Briefs match the current filter.
              </td>
            </tr>
          ) : (
            briefs.map((brief) => (
              <tr key={brief.id} className="align-top">
                <td className="px-4 py-4 font-mono text-xs text-muted-foreground">#{brief.sequenceNumber}</td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    <ClipboardList className="h-5 w-5 text-primary" />
                    <div>
                      <p className="font-semibold text-foreground">{brief.title}</p>
                      {brief.objective && <p className="mt-0.5 text-xs text-text-hint line-clamp-1">{brief.objective}</p>}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <RecommendationBadge status={brief.recommendationStatus} />
                </td>
                <td className="px-4 py-4">
                  <ApprovalBadge status={brief.approvalStatus} />
                </td>
                <td className="px-4 py-4 text-muted-foreground">{formatDate(brief.createdAt)}</td>
                <td className="px-4 py-4 text-xs text-text-hint">Session #{brief.chatSessionId}</td>
                <td className="px-4 py-4">
                  <button
                    type="button"
                    onClick={() => onOpen(brief.id)}
                    className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-foreground transition hover:bg-surface-subtle"
                  >
                    Open
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </section>
  )
}

function StatCard({ number, label, accent }: { number: string; label: string; accent: '' | 'blue' | 'amber' | 'red' }) {
  const accentColors = {
    '': '',
    blue: 'border-l-status-info',
    amber: 'border-l-status-processing',
    red: 'border-l-status-failed',
  }
  return (
    <div className={`rounded-xl border border-border bg-background p-4 pl-5 shadow-sm border-l-4 ${accentColors[accent]}`}>
      <p className="text-2xl font-semibold text-foreground">{number}</p>
      <p className="mt-1 text-sm text-muted-foreground">{label}</p>
    </div>
  )
}

function FilterDropdown({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (next: string) => void
  options: ReadonlyArray<{ value: string; label: string }>
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="appearance-none rounded-lg border border-border bg-background py-2 pl-3 pr-8 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="">{label}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronRight className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 rotate-90 text-text-hint" />
    </div>
  )
}

function Panel({ children }: { children: ReactNode }) {
  return <section className="rounded-2xl border border-border bg-background p-8 text-sm text-muted-foreground shadow-sm">{children}</section>
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-border bg-background p-10 text-center shadow-sm">
      <h3 className="font-heading text-lg font-semibold text-foreground">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
    </section>
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

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return value
  }
}
