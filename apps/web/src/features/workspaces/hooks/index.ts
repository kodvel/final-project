import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createWorkspace, getWorkspace, listWorkspaces } from '../api'

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
