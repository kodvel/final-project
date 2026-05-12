import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { VisualizationSnapshotQueryParams } from '../../../types/visualization'
import { getVisualizationSnapshot, refreshVisualizationSnapshot } from '../api'

export function visualizationSnapshotQueryKey(params: VisualizationSnapshotQueryParams) {
  return ['visualization-snapshot', params.workspaceId, params.periodStartMonth, params.periodEndMonth] as const
}

export function useVisualizationSnapshot(params: VisualizationSnapshotQueryParams) {
  return useQuery({
    queryKey: visualizationSnapshotQueryKey(params),
    queryFn: () => getVisualizationSnapshot(params),
    enabled: params.workspaceId > 0 && params.periodStartMonth.length > 0 && params.periodEndMonth.length > 0,
  })
}

export function useRefreshVisualizationSnapshot() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: refreshVisualizationSnapshot,
    onSuccess: (snapshot) => {
      queryClient.setQueryData(
        visualizationSnapshotQueryKey({
          workspaceId: snapshot.workspaceId,
          periodStartMonth: snapshot.periodStartMonth,
          periodEndMonth: snapshot.periodEndMonth,
        }),
        snapshot,
      )
    },
  })
}
