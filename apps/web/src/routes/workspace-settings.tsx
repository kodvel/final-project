import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import { useDeleteWorkspace, useUpdateWorkspace, useWorkspaces } from '../features/workspaces/hooks'
import { useActiveWorkspace } from '../features/workspaces/hooks/use-active-workspace'

export const Route = createFileRoute('/workspace-settings')({
  component: WorkspaceSettingsPage,
})

function WorkspaceSettingsPage() {
  const { activeWorkspace, setActiveWorkspace } = useActiveWorkspace()
  const navigate = useNavigate()
  const { refetch: refetchWorkspaces } = useWorkspaces()
  const updateWorkspace = useUpdateWorkspace()
  const deleteWorkspace = useDeleteWorkspace()

  if (!activeWorkspace) {
    return (
      <div className="h-full overflow-auto p-8">
        <section className="rounded-2xl border border-dashed border-border bg-background p-10 text-center shadow-sm">
          <h3 className="font-heading text-lg font-semibold text-foreground">No Workspace Selected</h3>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
            Select a workspace from the bottom-left switcher to manage its settings.
          </p>
        </section>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto p-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <header>
          <h1 className="font-heading text-2xl font-semibold tracking-tight text-foreground">Workspace Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">Manage <span className="font-medium text-foreground">{activeWorkspace.name}</span>.</p>
        </header>

        <GeneralCard
          key={activeWorkspace.id}
          initialName={activeWorkspace.name}
          initialDescription={activeWorkspace.description ?? ''}
          isPending={updateWorkspace.isPending}
          errorMessage={updateWorkspace.error instanceof Error ? updateWorkspace.error.message : null}
          onSave={(input) => updateWorkspace.mutateAsync({ workspaceId: activeWorkspace.id, input })}
        />

        <MetadataCard createdAt={activeWorkspace.createdAt} updatedAt={activeWorkspace.updatedAt} />

        <DangerZone
          workspaceName={activeWorkspace.name}
          isPending={deleteWorkspace.isPending}
          errorMessage={deleteWorkspace.error instanceof Error ? deleteWorkspace.error.message : null}
          onConfirmDelete={async () => {
            await deleteWorkspace.mutateAsync(activeWorkspace.id)
            const { data: remaining } = await refetchWorkspaces()
            setActiveWorkspace(remaining && remaining.length > 0 ? remaining[0] : null)
            navigate({ to: '/chat' })
          }}
        />
      </div>
    </div>
  )
}

function GeneralCard({
  initialName,
  initialDescription,
  isPending,
  errorMessage,
  onSave,
}: {
  initialName: string
  initialDescription: string
  isPending: boolean
  errorMessage: string | null
  onSave: (input: { name?: string; description?: string | null }) => Promise<unknown>
}) {
  const [name, setName] = useState(initialName)
  const [description, setDescription] = useState(initialDescription)
  const [savedAt, setSavedAt] = useState<number | null>(null)

  const trimmedName = name.trim()
  const dirty = trimmedName !== initialName.trim() || description !== initialDescription
  const valid = trimmedName.length > 0
  const canSave = dirty && valid && !isPending

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSave) return
    const payload: { name?: string; description?: string | null } = {}
    if (trimmedName !== initialName.trim()) payload.name = trimmedName
    if (description !== initialDescription) payload.description = description.length > 0 ? description : null
    await onSave(payload)
    setSavedAt(Date.now())
  }

  return (
    <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
      <h2 className="font-heading text-lg font-semibold text-foreground">General</h2>
      <p className="mt-1 text-sm text-muted-foreground">Rename the workspace or update its description.</p>

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
        <div>
          <label htmlFor="ws-name" className="block text-sm font-medium text-foreground">Name</label>
          <input
            id="ws-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
          />
          {!valid && <p className="mt-1 text-xs text-status-failed">Name cannot be empty.</p>}
        </div>

        <div>
          <label htmlFor="ws-description" className="block text-sm font-medium text-foreground">Description</label>
          <textarea
            id="ws-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>

        {errorMessage && (
          <p className="text-sm text-status-failed">{errorMessage}</p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!canSave}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Save changes
          </button>
          {savedAt && !dirty && !isPending && (
            <span className="text-xs text-muted-foreground">Saved.</span>
          )}
        </div>
      </form>
    </section>
  )
}

function MetadataCard({ createdAt, updatedAt }: { createdAt: string; updatedAt: string }) {
  return (
    <section className="rounded-2xl border border-border bg-background p-6 shadow-sm">
      <h2 className="font-heading text-lg font-semibold text-foreground">Details</h2>
      <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">Created</dt>
          <dd className="mt-1 text-foreground">{formatDate(createdAt)}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">Last updated</dt>
          <dd className="mt-1 text-foreground">{formatDate(updatedAt)}</dd>
        </div>
      </dl>
    </section>
  )
}

function DangerZone({
  workspaceName,
  isPending,
  errorMessage,
  onConfirmDelete,
}: {
  workspaceName: string
  isPending: boolean
  errorMessage: string | null
  onConfirmDelete: () => Promise<void>
}) {
  const [confirming, setConfirming] = useState(false)
  const [typed, setTyped] = useState('')

  const canDelete = typed === workspaceName && !isPending

  return (
    <section className="rounded-2xl border-2 border-destructive/60 bg-destructive/[0.04] p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
        <div className="flex-1">
          <h2 className="font-heading text-lg font-semibold text-destructive">Danger Zone</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Deleting a workspace permanently removes all of its sources, uploaded files, chat sessions, decision briefs, and visualizations. This cannot be undone.
          </p>

          {!confirming ? (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-destructive bg-background px-4 py-2 text-sm font-semibold text-destructive transition-colors hover:bg-destructive hover:text-destructive-foreground"
            >
              Delete workspace
            </button>
          ) : (
            <div className="mt-4 space-y-3">
              <label htmlFor="ws-confirm" className="block text-sm text-foreground">
                Type <span className="font-mono font-semibold">{workspaceName}</span> to confirm:
              </label>
              <input
                id="ws-confirm"
                type="text"
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                autoFocus
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-destructive focus:outline-none focus:ring-1 focus:ring-destructive"
              />
              {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  disabled={!canDelete}
                  onClick={() => {
                    void onConfirmDelete()
                  }}
                  className="inline-flex items-center gap-2 rounded-lg bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition-colors hover:bg-destructive/90 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Permanently delete
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setConfirming(false)
                    setTyped('')
                  }}
                  disabled={isPending}
                  className="rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-surface-subtle disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
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
