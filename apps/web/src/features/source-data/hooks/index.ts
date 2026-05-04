import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createSource, deleteSource, listSources, retrySource } from '../api'

export function useSources(workspaceId: number) {
  return useQuery({
    queryKey: ['sources', workspaceId],
    queryFn: () => listSources(workspaceId),
    enabled: workspaceId > 0,
  })
}

export function useCreateSource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useDeleteSource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useRetrySource() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: retrySource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}
