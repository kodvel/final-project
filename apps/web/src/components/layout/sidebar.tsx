import { Link, useLocation } from '@tanstack/react-router'
import { BarChart3, ChevronLeft, ChevronsUpDown, FolderOpen, MessageSquare, Plus } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { useCreateWorkspace, useWorkspaces } from '../../features/workspaces/hooks'
import { useActiveWorkspace } from '../../features/workspaces/hooks/use-active-workspace'
import type { Workspace } from '../../types/workspace'

const NAV_ITEMS = [
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/visualization-data', label: 'Visualization Data', icon: BarChart3 },
  { to: '/source-data', label: 'Source Data', icon: FolderOpen },
] as const

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <aside className={cn('flex h-screen flex-col bg-sidebar transition-[width] duration-200', collapsed ? 'w-[72px]' : 'w-[260px]')}>
      {/* Brand */}
      <div className={cn('flex items-center gap-3 px-5 pt-6 pb-4', collapsed && 'justify-center px-3')}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary">
          <span className="text-xs font-bold text-primary-foreground">IC</span>
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white leading-tight">Intelligence</p>
            <p className="truncate text-xs text-sidebar-foreground leading-tight">Copilot</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="mt-2 flex-1 px-3">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.to
            const Icon = item.icon
            return (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive ? 'bg-white/10 text-white' : 'text-sidebar-foreground hover:bg-white/5 hover:text-white',
                    collapsed && 'justify-center px-2',
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Workspace switcher */}
      <div className="border-t border-white/10 px-3 py-3">
        <WorkspaceSwitcher collapsed={collapsed} />
      </div>

      {/* Collapse toggle */}
      <div className="border-t border-white/10 px-3 py-3">
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className={cn(
            'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground transition-colors hover:bg-white/5 hover:text-white',
            collapsed && 'justify-center px-2',
          )}
        >
          <ChevronLeft className={cn('h-5 w-5 shrink-0 transition-transform', collapsed && 'rotate-180')} />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}

function WorkspaceSwitcher({ collapsed }: { collapsed: boolean }) {
  const { activeWorkspace, setActiveWorkspace } = useActiveWorkspace()
  const { data: workspaces, isLoading } = useWorkspaces()
  const createWorkspace = useCreateWorkspace()
  const [open, setOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const nameRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isCreating && nameRef.current) nameRef.current.focus()
  }, [isCreating])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
        setIsCreating(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  function handleSelect(ws: Workspace) {
    setActiveWorkspace(ws)
    setOpen(false)
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
          setOpen(false)
        },
      },
    )
  }

  return (
    <div className="relative" ref={containerRef}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-white/5',
          collapsed && 'justify-center px-2',
        )}
      >
        <div className="grid h-7 w-7 shrink-0 place-items-center rounded bg-white/10">
          <ChevronsUpDown className="h-4 w-4 text-sidebar-foreground" />
        </div>
        {!collapsed && (
          <div className="min-w-0 text-left">
            <p className="truncate text-sm text-white leading-tight">{activeWorkspace?.name ?? 'Select workspace'}</p>
            <p className="text-xs text-sidebar-foreground leading-tight">Switch workspace</p>
          </div>
        )}
      </button>

      {/* Popover */}
      {open && (
        <div
          className={cn(
            'absolute z-50 overflow-hidden rounded-xl bg-sidebar-accent shadow-xl border border-white/10',
            collapsed ? 'bottom-0 left-full ml-2 w-56' : 'bottom-0 left-0 right-0',
          )}
        >
          <div className="px-3 py-2 border-b border-white/10">
            <span className="text-xs font-semibold uppercase tracking-wider text-sidebar-foreground">Switch Workspace</span>
          </div>

          {isLoading && <p className="px-4 py-3 text-sm text-sidebar-foreground">Loading...</p>}
          {!isLoading && workspaces?.length === 0 && <p className="px-4 py-3 text-sm text-sidebar-foreground">No workspaces yet.</p>}

          {workspaces && workspaces.length > 0 && (
            <ul className="max-h-48 overflow-y-auto py-1">
              {workspaces.map((ws) => (
                <li key={ws.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(ws)}
                    className={cn(
                      'w-full text-left px-4 py-2 text-sm transition-colors hover:bg-white/5',
                      activeWorkspace?.id === ws.id ? 'bg-white/10 text-white font-semibold' : 'text-sidebar-foreground',
                    )}
                  >
                    {ws.name}
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="border-t border-white/10 px-3 py-3">
            {isCreating ? (
              <form onSubmit={handleCreate} className="space-y-2">
                <input
                  ref={nameRef}
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Workspace name"
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white placeholder:text-sidebar-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={createWorkspace.isPending}
                    className="flex-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                  >
                    {createWorkspace.isPending ? 'Creating...' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsCreating(false)}
                    className="rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-sidebar-foreground transition-colors hover:bg-white/5"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-white/5"
              >
                <Plus className="h-4 w-4" />
                New Workspace
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
