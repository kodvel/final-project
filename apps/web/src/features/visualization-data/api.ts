import { apiFetch } from '../../lib/api-client'
import type { VisualizationSnapshot, VisualizationSnapshotApi, VisualizationSnapshotQueryParams } from '../../types/visualization'

function fromApi(snapshot: VisualizationSnapshotApi): VisualizationSnapshot {
  return {
    id: snapshot.id,
    workspaceId: snapshot.workspace_id,
    periodStartMonth: snapshot.period_start_month,
    periodEndMonth: snapshot.period_end_month,
    contentJson: snapshot.content_json,
    sourceIds: snapshot.source_ids_json,
    artifactIds: snapshot.artifact_ids_json,
    status: snapshot.status,
    generationError: snapshot.generation_error,
    generatedAt: snapshot.generated_at,
    updatedAt: snapshot.updated_at,
  }
}

function buildQueryParams(params: VisualizationSnapshotQueryParams) {
  return new URLSearchParams({
    workspace_id: String(params.workspaceId),
    period_start_month: params.periodStartMonth,
    period_end_month: params.periodEndMonth,
  })
}

export async function getVisualizationSnapshot(params: VisualizationSnapshotQueryParams): Promise<VisualizationSnapshot> {
  const snapshot = await apiFetch<VisualizationSnapshotApi>(`/visualizations?${buildQueryParams(params)}`)
  return fromApi(snapshot)
}

export async function refreshVisualizationSnapshot(params: VisualizationSnapshotQueryParams): Promise<VisualizationSnapshot> {
  const snapshot = await apiFetch<VisualizationSnapshotApi>(`/visualizations/refresh?${buildQueryParams(params)}`, {
    method: 'POST',
  })
  return fromApi(snapshot)
}
