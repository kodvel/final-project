import { createContext, type ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useWorkspace } from './index'
import type { Workspace } from '../../../types/workspace'

const STORAGE_KEY = 'activeWorkspaceId'

function readStoredId(): number | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null) return null
    const id = Number(raw)
    if (!Number.isInteger(id) || id <= 0) {
      localStorage.removeItem(STORAGE_KEY)
      return null
    }
    return id
  } catch {
    return null
  }
}

function writeStoredId(id: number | null): void {
  try {
    if (id === null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, String(id))
    }
  } catch {
    // localStorage unavailable — ignore silently
  }
}

type WorkspaceContextValue = {
  activeWorkspaceId: number | null
  setActiveWorkspaceId: (id: number | null) => void
  activeWorkspace: Workspace | null
  setActiveWorkspace: (ws: Workspace | null) => void
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

type WorkspaceProviderProps = {
  children: ReactNode
  initialWorkspaceId?: number | null
}

export function WorkspaceProvider({ children, initialWorkspaceId }: WorkspaceProviderProps) {
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<number | null>(initialWorkspaceId ?? null)
  const hydratedRef = useRef(false)

  // SSR-safe: read localStorage only after mount, never during server render
  useEffect(() => {
    if (hydratedRef.current) return
    hydratedRef.current = true
    if (initialWorkspaceId !== undefined && initialWorkspaceId !== null) return
    const storedId = readStoredId()
    if (storedId !== null) {
      setActiveWorkspaceIdState(storedId)
    }
  }, [initialWorkspaceId])

  // Derive activeWorkspace from activeWorkspaceId via the shared query cache
  // useWorkspace disables the query when id <= 0, so it returns undefined when no workspace is selected
  const { data: fetchedWorkspace } = useWorkspace(activeWorkspaceId ?? 0)
  const activeWorkspace = fetchedWorkspace ?? null

  const queryClient = useQueryClient()

  const setActiveWorkspaceId = useCallback((id: number | null) => {
    setActiveWorkspaceIdState(id)
    writeStoredId(id)
  }, [])

  const setActiveWorkspace = useCallback((ws: Workspace | null) => {
    const id = ws?.id ?? null
    setActiveWorkspaceIdState(id)
    writeStoredId(id)
    if (ws) {
      // Populate cache so useWorkspace resolves immediately without a refetch
      queryClient.setQueryData(['workspaces', id], ws)
    }
  }, [queryClient])

  return (
    <WorkspaceContext.Provider value={{ activeWorkspaceId, setActiveWorkspaceId, activeWorkspace, setActiveWorkspace }}>
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useActiveWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error('useActiveWorkspace must be used within WorkspaceProvider')
  return ctx
}

export function useActiveWorkspaceId(): number | null {
  return useActiveWorkspace().activeWorkspaceId
}
