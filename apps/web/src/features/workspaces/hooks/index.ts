import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createWorkspace, deleteWorkspace, getWorkspace, listWorkspaces, updateWorkspace } from '../api'
import type { UpdateWorkspaceInput, Workspace } from '../../../types/workspace'

export function useWorkspaces() {
  return useQuery({
    queryKey: ['workspaces'],
    queryFn: listWorkspaces,
  })
}

export function useWorkspace(workspaceId: number) {
  return useQuery({
    queryKey: ['workspaces', workspaceId],
    queryFn: () => getWorkspace(workspaceId),
    enabled: workspaceId > 0,
  })
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createWorkspace,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useUpdateWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ workspaceId, input }: { workspaceId: number; input: UpdateWorkspaceInput }) =>
      updateWorkspace(workspaceId, input),
    onSuccess: (updated: Workspace) => {
      queryClient.setQueryData(['workspaces', updated.id], updated)
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (workspaceId: number) => deleteWorkspace(workspaceId).then(() => workspaceId),
    onSuccess: (workspaceId: number) => {
      queryClient.removeQueries({ queryKey: ['workspaces', workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      queryClient.invalidateQueries({ queryKey: ['chat-session'] })
      queryClient.invalidateQueries({ queryKey: ['decision-briefs'] })
      queryClient.invalidateQueries({ queryKey: ['decision-brief'] })
      queryClient.invalidateQueries({ queryKey: ['visualization-snapshot'] })
    },
  })
}
