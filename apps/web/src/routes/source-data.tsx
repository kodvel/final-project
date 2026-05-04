import { createFileRoute } from '@tanstack/react-router'
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

  return (
    <main className="p-6 lg:p-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[#626A7C]">Source Data</p>
          <h2 className="text-3xl font-semibold tracking-tight text-[#151826]">Manage uploaded Sources</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#626A7C]">
            Upload CSV and PDF Sources, label them by team/category/period, and track Processing Status for the Active Workspace.
          </p>
        </div>
        <button
          type="button"
          disabled={!activeWorkspace}
          onClick={() => setIsDialogOpen(true)}
          className="rounded-xl bg-[#4F46E5] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#3525cd] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Add New Data
        </button>
      </div>

      {!activeWorkspace ? (
        <EmptyState title="Select a Workspace" description="Choose or create a Workspace from the header before adding Sources." />
      ) : isLoading ? (
        <Panel>Loading Sources...</Panel>
      ) : error ? (
        <Panel>Could not load Sources. Check that the API is running.</Panel>
      ) : sources.length === 0 ? (
        <EmptyState title="No Sources yet" description="Upload a CSV or PDF Source to start building this Workspace's company memory." />
      ) : (
        <SourceTable
          sources={sources}
          onDelete={(sourceId) => {
            if (window.confirm('Delete this Source? Past citations remain auditable.')) deleteSource.mutate(sourceId)
          }}
          onRetry={(sourceId) => retrySource.mutate(sourceId)}
        />
      )}

      {isDialogOpen && activeWorkspace && (
        <AddSourceDialog
          workspaceId={activeWorkspace.id}
          isSubmitting={createSource.isPending}
          onClose={() => setIsDialogOpen(false)}
          onSubmit={(input) => createSource.mutate(input, { onSuccess: () => setIsDialogOpen(false) })}
        />
      )}
    </main>
  )
}

function Panel({ children }: { children: ReactNode }) {
  return <section className="rounded-2xl border border-[#E5E2F0] bg-white p-8 text-sm text-[#626A7C] shadow-sm">{children}</section>
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-[#C7C4D8] bg-white p-10 text-center shadow-sm">
      <h3 className="text-lg font-semibold text-[#151826]">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#626A7C]">{description}</p>
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
    <section className="overflow-hidden rounded-2xl border border-[#E5E2F0] bg-white shadow-sm">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="bg-[#F4F2FA] text-xs uppercase tracking-wide text-[#626A7C]">
          <tr>
            <th className="px-4 py-3">Title</th>
            <th className="px-4 py-3">File</th>
            <th className="px-4 py-3">Team</th>
            <th className="px-4 py-3">Categories</th>
            <th className="px-4 py-3">Period</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Uploaded</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E5E2F0]">
          {sources.map((source) => (
            <tr key={source.id} className="align-top">
              <td className="px-4 py-4 font-semibold text-[#151826]">{source.title}</td>
              <td className="px-4 py-4 uppercase text-[#626A7C]">{source.fileType}</td>
              <td className="px-4 py-4">{formatLabel(source.teamLabel)}</td>
              <td className="px-4 py-4 text-[#626A7C]">{source.categoryLabels.map(formatLabel).join(', ')}</td>
              <td className="px-4 py-4 text-[#626A7C]">
                {source.periodLabel || [source.periodStart, source.periodEnd].filter(Boolean).join(' → ') || '—'}
              </td>
              <td className="px-4 py-4">
                <StatusBadge status={source.processingStatus} />
              </td>
              <td className="px-4 py-4 text-[#626A7C]">{new Date(source.uploadedAt).toLocaleDateString()}</td>
              <td className="space-x-2 px-4 py-4">
                {source.processingStatus === 'failed' && (
                  <button type="button" onClick={() => onRetry(source.id)} className="font-semibold text-[#0284C7] hover:underline">
                    Retry
                  </button>
                )}
                <button type="button" onClick={() => onDelete(source.id)} className="font-semibold text-[#E11D48] hover:underline">
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function StatusBadge({ status }: { status: SourceData['processingStatus'] }) {
  const color =
    status === 'ready'
      ? 'bg-[#DDF8F3] text-[#0F766E]'
      : status === 'failed'
        ? 'bg-[#FFE4E6] text-[#BE123C]'
        : status === 'processing'
          ? 'bg-[#E0F2FE] text-[#0369A1]'
          : 'bg-[#F4F2FA] text-[#626A7C]'
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${color}`}>{status}</span>
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#111A3A]/40 p-4">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (!file) return
          onSubmit({ workspaceId, title, file, teamLabel, categoryLabels, periodStart, periodEnd, periodLabel })
        }}
        className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold text-[#151826]">Add New Data</h3>
            <p className="mt-1 text-sm text-[#626A7C]">Upload one CSV or PDF Source for this Workspace.</p>
          </div>
          <button type="button" onClick={onClose} className="text-[#626A7C]">
            ✕
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="sm:col-span-2 text-sm font-medium text-[#151826]">
            Title
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#E5E2F0] px-3 py-2"
            />
          </label>
          <label className="sm:col-span-2 text-sm font-medium text-[#151826]">
            File
            <input
              required
              accept=".csv,.pdf"
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="mt-1 w-full rounded-lg border border-[#E5E2F0] px-3 py-2"
            />
          </label>
          <label className="text-sm font-medium text-[#151826]">
            Team Label
            <select
              value={teamLabel}
              onChange={(e) => setTeamLabel(e.target.value as TeamLabel)}
              className="mt-1 w-full rounded-lg border border-[#E5E2F0] px-3 py-2"
            >
              {TEAM_LABELS.map((label) => (
                <option key={label} value={label}>
                  {formatLabel(label)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-[#151826]">
            Category Labels
            <select
              multiple
              value={categoryLabels}
              onChange={(e) => setCategoryLabels(Array.from(e.target.selectedOptions, (option) => option.value as CategoryLabel))}
              className="mt-1 min-h-28 w-full rounded-lg border border-[#E5E2F0] px-3 py-2"
            >
              {CATEGORY_LABELS.map((label) => (
                <option key={label} value={label}>
                  {formatLabel(label)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-[#151826]">
            Period Start
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#E5E2F0] px-3 py-2"
            />
          </label>
          <label className="text-sm font-medium text-[#151826]">
            Period End
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#E5E2F0] px-3 py-2"
            />
          </label>
          <label className="sm:col-span-2 text-sm font-medium text-[#151826]">
            Period Label
            <input
              value={periodLabel}
              onChange={(e) => setPeriodLabel(e.target.value)}
              placeholder="Q1 2026, April 2026, etc."
              className="mt-1 w-full rounded-lg border border-[#E5E2F0] px-3 py-2"
            />
          </label>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button type="button" onClick={onClose} className="rounded-lg border border-[#E5E2F0] px-4 py-2 text-sm font-semibold text-[#626A7C]">
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-lg bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
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
