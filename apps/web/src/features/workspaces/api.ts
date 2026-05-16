import { apiFetch } from '../../lib/api-client'
import type { CreateWorkspaceInput, UpdateWorkspaceInput, Workspace, WorkspaceApi } from '../../types/workspace'

function fromApi(workspace: WorkspaceApi): Workspace {
  return {
    id: workspace.id,
    name: workspace.name,
    description: workspace.description,
    createdAt: workspace.created_at,
    updatedAt: workspace.updated_at ?? workspace.created_at,
  }
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const workspaces = await apiFetch<WorkspaceApi[]>('/workspaces')
  return workspaces.map(fromApi)
}

export async function getWorkspace(workspaceId: number): Promise<Workspace> {
  return fromApi(await apiFetch<WorkspaceApi>(`/workspaces/${workspaceId}`))
}

export async function createWorkspace(input: CreateWorkspaceInput): Promise<Workspace> {
  return fromApi(
    await apiFetch<WorkspaceApi>('/workspaces', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  )
}

export async function updateWorkspace(workspaceId: number, input: UpdateWorkspaceInput): Promise<Workspace> {
  return fromApi(
    await apiFetch<WorkspaceApi>(`/workspaces/${workspaceId}`, {
      method: 'PATCH',
      body: JSON.stringify(input),
    }),
  )
}

export async function deleteWorkspace(workspaceId: number): Promise<void> {
  await apiFetch<void>(`/workspaces/${workspaceId}`, { method: 'DELETE' })
}
