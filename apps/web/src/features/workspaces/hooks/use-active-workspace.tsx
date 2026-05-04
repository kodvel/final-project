import { createContext, type ReactNode, useCallback, useContext, useState } from 'react'
import type { Workspace } from '../../../types/workspace'

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

export function WorkspaceProvider({ children, initialWorkspaceId = null }: WorkspaceProviderProps) {
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<number | null>(initialWorkspaceId)
  const [activeWorkspace, setActiveWorkspaceState] = useState<Workspace | null>(null)

  const setActiveWorkspaceId = useCallback((id: number | null) => {
    setActiveWorkspaceIdState(id)
    if (id === null) {
      setActiveWorkspaceState(null)
    }
  }, [])

  const setActiveWorkspace = useCallback((ws: Workspace | null) => {
    setActiveWorkspaceState(ws)
    setActiveWorkspaceIdState(ws?.id ?? null)
  }, [])

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
