import type { FormEvent } from 'react'
import { useEffect, useRef, useState } from 'react'
import type { Workspace } from '../../../types/workspace'
import { useCreateWorkspace, useWorkspaces } from '../hooks'
import { useActiveWorkspace } from '../hooks/use-active-workspace'

export function WorkspaceSelector() {
  const { data: workspaces, isLoading } = useWorkspaces()
  const createWorkspace = useCreateWorkspace()
  const { activeWorkspace, setActiveWorkspace } = useActiveWorkspace()

  const [isCreating, setIsCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const nameInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isCreating && nameInputRef.current) {
      nameInputRef.current.focus()
    }
  }, [isCreating])

  function handleSelect(ws: Workspace) {
    setActiveWorkspace(ws)
    setShowDropdown(false)
  }

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    createWorkspace.mutate(
      { name: newName.trim() },
      {
        onSuccess: (ws) => {
          setActiveWorkspace(ws)
          setNewName('')
          setIsCreating(false)
          setShowDropdown(false)
        },
      },
    )
  }

  return (
    <div className="relative">
      {/* Current workspace trigger */}
      <button
        type="button"
        onClick={() => setShowDropdown((v) => !v)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border-subtle bg-white text-sm font-medium text-secondary-foreground hover:border-primary transition-colors"
      >
        <span className="text-primary">📁</span>
        <span>{activeWorkspace?.name ?? 'Select workspace'}</span>
        <span className="text-xs text-text-hint">▼</span>
      </button>

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-border-subtle rounded-xl shadow-lg z-50 overflow-hidden">
          <div className="px-3 py-2 border-b border-border-subtle">
            <span className="text-xs font-semibold text-on-secondary uppercase tracking-wider">Switch Workspace</span>
          </div>

          {isLoading && <p className="px-4 py-3 text-sm text-text-hint">Loading...</p>}

          {workspaces && workspaces.length === 0 && <p className="px-4 py-3 text-sm text-text-hint">No workspaces yet.</p>}

          {workspaces && workspaces.length > 0 && (
            <ul className="max-h-48 overflow-y-auto py-1">
              {workspaces.map((ws) => (
                <li key={ws.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(ws)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-surface-subtle transition-colors ${
                      activeWorkspace?.id === ws.id ? 'bg-surface-subtle text-primary font-semibold' : 'text-secondary-foreground'
                    }`}
                  >
                    {ws.name}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Create new workspace */}
          <div className="border-t border-border-subtle px-3 py-3">
            {isCreating ? (
              <form onSubmit={handleCreate} className="space-y-2">
                <input
                  ref={nameInputRef}
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Workspace name"
                  className="w-full px-3 py-1.5 text-sm border border-border-subtle rounded-lg focus:outline-none focus:border-primary"
                />
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={createWorkspace.isPending}
                    className="flex-1 px-3 py-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50"
                  >
                    {createWorkspace.isPending ? 'Creating...' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsCreating(false)}
                    className="px-3 py-1.5 text-xs font-medium text-on-secondary border border-border-subtle rounded-lg hover:bg-surface-subtle transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="w-full text-left px-3 py-1.5 text-sm font-medium text-primary hover:bg-surface-subtle rounded-lg transition-colors"
              >
                + New Workspace
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
