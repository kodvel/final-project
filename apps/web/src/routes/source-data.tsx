import { createFileRoute } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, FileSpreadsheet, FileText, Plus, RefreshCw, Search, Trash2, Upload } from 'lucide-react'
import type { ReactNode } from 'react'
import { useState } from 'react'
import { useCreateSource, useDeleteSource, useRetrySource, useSources } from '../features/source-data/hooks'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'
import type { CategoryLabel, TeamLabel } from '../types/common'
import type { CreateSourceInput, SourceData } from '../types/source'

export const Route = createFileRoute('/source-data')({
  component: SourceDataPage,
})

function SourceDataPage() {
  const { activeWorkspace } = useActiveWorkspace()
  const workspaceId = activeWorkspace?.id ?? 0
  const { data: sources = [], isLoading, error } = useSources(workspaceId)
  const createSource = useCreateSource()
  const deleteSource = useDeleteSource()
  const retrySource = useRetrySource()
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Derive stats from source data if available, otherwise mock
  const totalSources = sources.length
  const readyCount = sources.filter((s) => s.processingStatus === 'ready').length
  const processingCount = sources.filter((s) => s.processingStatus === 'processing').length
  const failedCount = sources.filter((s) => s.processingStatus === 'failed').length

  // Mock numbers when no real data
  const displayTotal = totalSources > 0 ? totalSources : 1248
  const displayReady = readyCount > 0 ? readyCount : 1192
  const displayProcessing = processingCount > 0 ? processingCount : 45
  const displayFailed = failedCount > 0 ? failedCount : 11

  return (
    <div className="h-full overflow-auto p-8">
      {!activeWorkspace ? (
        <EmptyState title="Select a Workspace" description="Choose or create a Workspace from the header before adding Sources." />
      ) : isLoading ? (
        <Panel>Loading Sources...</Panel>
      ) : error ? (
        <Panel>Could not load Sources. Check that the API is running.</Panel>
      ) : (
        <>
          {/* Header row */}
          <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">Source Library</h1>
              <p className="mt-1 text-sm text-muted-foreground">Single source of truth for company context</p>
            </div>
            <button
              type="button"
              onClick={() => setIsDialogOpen(true)}
              className="mt-4 flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary-hover sm:mt-0"
            >
              <Plus className="h-4 w-4" />
              Add New Data
            </button>
          </div>

          {/* Stats cards row */}
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard number={displayTotal.toLocaleString()} label="Total Sources" accent="" />
            <StatCard number={displayReady.toLocaleString()} label="Ready" accent="blue" />
            <StatCard number={displayProcessing.toLocaleString()} label="Processing" accent="amber" />
            <StatCard number={displayFailed.toLocaleString()} label="Failed" accent="red" />
          </div>

          {/* Filter bar */}
          <div className="mb-4 flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-hint" />
              <input
                type="text"
                placeholder="Search sources..."
                className="w-full rounded-lg border border-border bg-background py-2 pl-10 pr-4 text-sm text-foreground placeholder-text-hint focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <FilterDropdown label="Team" options={['Marketing', 'Product', 'Data Analysis', 'Business']} />
            <FilterDropdown
              label="Category"
              options={[
                'Analytics Metrics',
                'Market Research',
                'Product Feature',
                'Customer Insight',
                'Business Model',
                'Competitor Analysis',
                'Revenue Sales',
              ]}
            />
            <FilterDropdown label="Period" options={['Q1 2026', 'Q2 2026', 'Q3 2026', 'Q4 2026']} />
            <FilterDropdown label="Type" options={['CSV', 'PDF']} />
            <FilterDropdown label="Status" options={['Ready', 'Processing', 'Uploaded', 'Failed']} />
          </div>

          {/* Table */}
          <SourceTable
            sources={sources}
            onDelete={(sourceId) => {
              if (window.confirm('Delete this Source? Past citations remain auditable.')) deleteSource.mutate(sourceId)
            }}
            onRetry={(sourceId) => retrySource.mutate(sourceId)}
          />

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing 1 to {sources.length} of {displayTotal.toLocaleString()} sources
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
        </>
      )}

      {isDialogOpen && activeWorkspace && (
        <AddSourceDialog
          workspaceId={activeWorkspace.id}
          isSubmitting={createSource.isPending}
          onClose={() => setIsDialogOpen(false)}
          onSubmit={(input) => createSource.mutate(input, { onSuccess: () => setIsDialogOpen(false) })}
        />
      )}
    </div>
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

function FilterDropdown({ label, options }: { label: string; options: string[] }) {
  const [selected, setSelected] = useState<string>('')
  return (
    <div className="relative">
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="appearance-none rounded-lg border border-border bg-background py-2 pl-3 pr-8 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="">{label}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
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

function SourceTable({
  sources,
  onDelete,
  onRetry,
}: {
  sources: SourceData[]
  onDelete: (sourceId: number) => void
  onRetry: (sourceId: number) => void
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-background shadow-sm">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3">File</th>
            <th className="px-4 py-3">Team</th>
            <th className="px-4 py-3">Category</th>
            <th className="px-4 py-3">Period</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {sources.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-4 py-8 text-center text-text-hint">
                No sources found. Upload a CSV or PDF to get started.
              </td>
            </tr>
          ) : (
            sources.map((source) => (
              <tr key={source.id} className="align-top">
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    {source.fileType === 'pdf' ? (
                      <FileText className="h-5 w-5 text-status-failed-foreground" />
                    ) : (
                      <FileSpreadsheet className="h-5 w-5 text-status-ready-foreground" />
                    )}
                    <div>
                      <p className="font-semibold text-foreground">{source.title}</p>
                      <p className="mt-0.5 text-xs uppercase text-text-hint">{source.fileType}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4 text-foreground">{formatLabel(source.teamLabel)}</td>
                <td className="px-4 py-4 text-muted-foreground">{source.categoryLabels.map(formatLabel).join(', ')}</td>
                <td className="px-4 py-4 text-muted-foreground">
                  {source.periodLabel || [source.periodStart, source.periodEnd].filter(Boolean).join(' → ') || '—'}
                </td>
                <td className="px-4 py-4">
                  <StatusBadge status={source.processingStatus} />
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-2">
                    {source.processingStatus === 'failed' && (
                      <button
                        type="button"
                        onClick={() => onRetry(source.id)}
                        className="flex items-center gap-1 text-xs font-semibold text-status-info-foreground hover:underline"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                        Retry
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => onDelete(source.id)}
                      className="flex items-center gap-1 text-xs font-semibold text-status-failed-foreground hover:underline"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </section>
  )
}

function StatusBadge({ status }: { status: SourceData['processingStatus'] }) {
  const colorMap = {
    ready: 'bg-status-ready text-status-ready-foreground',
    processing: 'bg-status-processing text-status-processing-foreground',
    uploaded: 'bg-status-info text-status-info-foreground',
    failed: 'bg-status-failed text-status-failed-foreground',
  }
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${colorMap[status]}`}>{status}</span>
}

function AddSourceDialog({
  workspaceId,
  isSubmitting,
  onClose,
  onSubmit,
}: {
  workspaceId: number
  isSubmitting: boolean
  onClose: () => void
  onSubmit: (input: CreateSourceInput) => void
}) {
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [teamLabel, setTeamLabel] = useState<TeamLabel>('marketing')
  const [categoryLabels, setCategoryLabels] = useState<CategoryLabel[]>(['analytics_metrics'])
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [periodLabel, setPeriodLabel] = useState('')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (!file) return
          onSubmit({ workspaceId, title, file, teamLabel, categoryLabels, periodStart, periodEnd, periodLabel })
        }}
        className="w-full max-w-2xl rounded-2xl bg-background p-6 shadow-xl"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h3 className="font-heading text-xl font-semibold text-foreground">Add New Data</h3>
            <p className="mt-1 text-sm text-muted-foreground">Upload one CSV or PDF Source for this Workspace.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-muted-foreground hover:bg-surface-subtle transition">
            ✕
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium text-foreground sm:col-span-2">
            Title
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder-text-hint focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </label>
          <label className="text-sm font-medium text-foreground sm:col-span-2">
            File
            <input
              required
              accept=".csv,.pdf"
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </label>
          <label className="text-sm font-medium text-foreground">
            Team Label
            <select
              value={teamLabel}
              onChange={(e) => setTeamLabel(e.target.value as TeamLabel)}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {TEAM_LABELS.map((label) => (
                <option key={label} value={label}>
                  {formatLabel(label)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-foreground">
            Category Labels
            <select
              multiple
              value={categoryLabels}
              onChange={(e) => setCategoryLabels(Array.from(e.target.selectedOptions, (option) => option.value as CategoryLabel))}
              className="mt-1 min-h-28 w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {CATEGORY_LABELS.map((label) => (
                <option key={label} value={label}>
                  {formatLabel(label)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-foreground">
            Period Start
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </label>
          <label className="text-sm font-medium text-foreground">
            Period End
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </label>
          <label className="text-sm font-medium text-foreground sm:col-span-2">
            Period Label
            <input
              value={periodLabel}
              onChange={(e) => setPeriodLabel(e.target.value)}
              placeholder="Q1 2026, April 2026, etc."
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder-text-hint focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </label>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-muted-foreground transition hover:bg-surface-subtle"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hover disabled:opacity-50"
          >
            <Upload className="h-4 w-4" />
            {isSubmitting ? 'Uploading...' : 'Upload Source'}
          </button>
        </div>
      </form>
    </div>
  )
}

const TEAM_LABELS: TeamLabel[] = ['marketing', 'product', 'data_analysis', 'business']
const CATEGORY_LABELS: CategoryLabel[] = [
  'analytics_metrics',
  'market_research',
  'product_feature',
  'customer_insight',
  'business_model',
  'competitor_analysis',
  'revenue_sales',
]

function formatLabel(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}
