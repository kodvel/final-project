import { useQuery } from '@tanstack/react-query'
import type { VisualizationFilters } from '../../../types/visualization'
import { extractKpisFromArtifacts, getInsightArtifacts, getPrimaryChartArtifact, listVisualizationArtifacts } from '../api'

export function useVisualizationArtifacts(filters: VisualizationFilters) {
  return useQuery({
    queryKey: ['visualizations', filters],
    queryFn: () => listVisualizationArtifacts(filters),
    enabled: filters.workspaceId > 0,
  })
}

// Derived hooks for specific data needs

export function useKpiCards(filters: VisualizationFilters) {
  const { data: artifacts = [], ...rest } = useVisualizationArtifacts(filters)
  return {
    ...rest,
    data: extractKpisFromArtifacts(artifacts),
  }
}

export function usePrimaryChart(filters: VisualizationFilters) {
  const { data: artifacts = [], ...rest } = useVisualizationArtifacts(filters)
  return {
    ...rest,
    data: getPrimaryChartArtifact(artifacts),
  }
}

export function useInsightCards(filters: VisualizationFilters) {
  const { data: artifacts = [], ...rest } = useVisualizationArtifacts(filters)
  return {
    ...rest,
    data: getInsightArtifacts(artifacts),
  }
}
