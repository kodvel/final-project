import { apiFetch } from '../../lib/api-client'
import type {
  ChartSpecContent,
  CsvProfileContent,
  InsightCardContent,
  VisualizationArtifact,
  VisualizationArtifactApi,
  VisualizationArtifactContent,
  VisualizationFilters,
} from '../../types/visualization'

function fromApi(
  artifact: VisualizationArtifactApi,
  sourceMeta?: {
    sourceTitle?: string
    sourceFileType?: 'csv' | 'pdf'
    teamLabel?: string
    categoryLabels?: string[]
  },
): VisualizationArtifact {
  return {
    id: artifact.id,
    sourceId: artifact.source_id,
    artifactType: artifact.artifact_type,
    title: artifact.title,
    contentJson: artifact.content_json,
    sourceTitle: artifact.source_title ?? sourceMeta?.sourceTitle,
    sourceFileType: artifact.source_file_type ?? sourceMeta?.sourceFileType,
    teamLabel: artifact.team_label ?? (sourceMeta?.teamLabel as VisualizationArtifact['teamLabel']),
    categoryLabels: artifact.category_labels ?? (sourceMeta?.categoryLabels as VisualizationArtifact['categoryLabels']),
  }
}

export async function listVisualizationArtifacts(filters: VisualizationFilters): Promise<VisualizationArtifact[]> {
  const params = new URLSearchParams({ workspace_id: String(filters.workspaceId) })
  if (filters.teamLabel) params.set('team_label', filters.teamLabel)
  if (filters.categoryLabel) params.set('category_label', filters.categoryLabel)
  if (filters.periodStart) params.set('period_start', filters.periodStart)
  if (filters.periodEnd) params.set('period_end', filters.periodEnd)

  const artifacts = await apiFetch<VisualizationArtifactApi[]>(`/visualizations?${params}`)
  return artifacts.map((a) => fromApi(a))
}

export async function getVisualizationArtifactsBySource(sourceId: number): Promise<VisualizationArtifact[]> {
  const artifacts = await apiFetch<VisualizationArtifactApi[]>(`/visualizations/${sourceId}`)
  return artifacts.map((a) => fromApi(a))
}

// Type guards for artifact content
export function isCsvProfile(content: VisualizationArtifactContent): content is CsvProfileContent {
  return typeof content === 'object' && content !== null && 'total_rows' in content
}

export function isChartSpec(content: VisualizationArtifactContent): content is ChartSpecContent {
  return typeof content === 'object' && content !== null && 'chart_type' in content
}

export function isInsightCard(content: VisualizationArtifactContent): content is InsightCardContent {
  return typeof content === 'object' && content !== null && 'insight_type' in content
}

// Helper to extract KPIs from chart_spec artifacts
export function extractKpisFromArtifacts(artifacts: VisualizationArtifact[]): Array<{
  label: string
  value: string
  delta?: string
  trend?: 'up' | 'down'
  sourceTitle?: string
}> {
  const kpis: Array<{
    label: string
    value: string
    delta?: string
    trend?: 'up' | 'down'
    sourceTitle?: string
  }> = []

  for (const artifact of artifacts) {
    if (artifact.artifactType === 'chart_spec' && isChartSpec(artifact.contentJson)) {
      const spec = artifact.contentJson
      if (spec.kpis) {
        for (const kpi of spec.kpis) {
          kpis.push({ ...kpi, sourceTitle: artifact.sourceTitle })
        }
      }
    }
  }

  return kpis
}

// Helper to get chart artifact for the main chart display
export function getPrimaryChartArtifact(artifacts: VisualizationArtifact[]): VisualizationArtifact | null {
  return artifacts.find((a) => a.artifactType === 'chart_spec' && isChartSpec(a.contentJson)) ?? null
}

// Helper to get insight/ anomaly artifacts
export function getInsightArtifacts(artifacts: VisualizationArtifact[]): VisualizationArtifact[] {
  return artifacts.filter((a) => a.artifactType === 'insight_card' && isInsightCard(a.contentJson))
}
