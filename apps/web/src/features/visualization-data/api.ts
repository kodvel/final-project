import { apiFetch } from '../../lib/api-client'
import type { VisualizationSnapshot, VisualizationSnapshotApi, VisualizationSnapshotQueryParams } from '../../types/visualization'

function mapEvidenceRef(ref: any) {
  return {
    sourceId: ref?.sourceId ?? ref?.source_id,
    sourceTitle: ref?.sourceTitle ?? ref?.source_title,
    artifactId: ref?.artifactId ?? ref?.artifact_id,
    quote: ref?.quote,
    pageNumber: ref?.pageNumber ?? ref?.page_number,
  }
}

function mapItem(item: any) {
  if (typeof item === 'string') return { kind: 'gap' as const, text: item }
  return {
    ...item,
    evidenceRefs: (item?.evidenceRefs ?? item?.evidence_refs ?? item?.evidence ?? []).map(mapEvidenceRef),
  }
}

function mapSourceCard(card: any) {
  return {
    ...card,
    sourceId: card?.sourceId ?? card?.source_id,
    sourceFileType: card?.sourceFileType ?? card?.source_file_type ?? card?.file_type,
    teamLabel: card?.teamLabel ?? card?.team_label,
    categoryLabels: card?.categoryLabels ?? card?.category_labels ?? [],
    periodLabel: card?.periodLabel ?? card?.period_label,
    evidenceRefs: (card?.evidenceRefs ?? card?.evidence_refs ?? []).map(mapEvidenceRef),
  }
}

function mapContent(content: any) {
  const coverage = content?.coverage ?? {}
  return {
    ...content,
    coverage: {
      ...coverage,
      totalSources: coverage.totalSources ?? coverage.total_sources,
      readySources: coverage.readySources ?? coverage.ready_sources,
      excludedSources: coverage.excludedSources ?? coverage.excluded_sources,
    },
    source_cards: (content?.source_cards ?? content?.sourceCards ?? []).map(mapSourceCard),
    key_findings: (content?.key_findings ?? content?.keyFindings ?? []).map(mapItem),
    risks_assumptions: (content?.risks_assumptions ?? content?.risksAssumptions ?? []).map(mapItem),
    opportunities: (content?.opportunities ?? []).map(mapItem),
    cross_source_patterns: (content?.cross_source_patterns ?? content?.crossSourcePatterns ?? []).map(mapItem),
    gaps: (content?.gaps ?? []).map(mapItem),
  }
}

function fromApi(snapshot: VisualizationSnapshotApi): VisualizationSnapshot {
  return {
    id: snapshot.id,
    workspaceId: snapshot.workspace_id,
    periodStartMonth: snapshot.period_start_month,
    periodEndMonth: snapshot.period_end_month,
    contentJson: mapContent(snapshot.content_json),
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
  const snapshot = await apiFetch<VisualizationSnapshotApi>('/visualizations/refresh', {
    method: 'POST',
    body: JSON.stringify({
      workspace_id: params.workspaceId,
      period_start_month: params.periodStartMonth,
      period_end_month: params.periodEndMonth,
    }),
  })
  return fromApi(snapshot)
}
