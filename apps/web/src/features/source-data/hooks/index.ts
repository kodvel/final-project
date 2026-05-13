import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createSource, deleteSource, listSources, retrySource } from '../api'

const POLL_INTERVAL_MS = 3_000

const INCOMPLETE_STATUSES: Set<string> = new Set(['uploaded', 'processing'])

export function useSources(workspaceId: number) {
  return useQuery({
    queryKey: ['sources', workspaceId],
    queryFn: () => listSources(workspaceId),
    enabled: workspaceId > 0,
    refetchInterval: (query) => {
      if (!workspaceId) return false
      const sources = query.state.data
      if (!sources || sources.length === 0) return false
      const hasIncomplete = sources.some((s) => INCOMPLETE_STATUSES.has(s.processingStatus))
      return hasIncomplete ? POLL_INTERVAL_MS : false
    },
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
