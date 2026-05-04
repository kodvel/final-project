import { apiFetch } from '../../lib/api-client'
import type { CreateSourceInput, SourceData, SourceDataApi } from '../../types/source'

function fromApi(source: SourceDataApi): SourceData {
  return {
    id: source.id,
    workspaceId: source.workspace_id,
    title: source.title,
    teamLabel: source.team_label,
    categoryLabels: source.category_labels,
    fileType: source.file_type,
    originalFilename: source.original_filename,
    storagePath: source.storage_path,
    periodStart: source.period_start,
    periodEnd: source.period_end,
    periodLabel: source.period_label,
    processingStatus: source.processing_status,
    processingError: source.processing_error,
    uploadedAt: source.uploaded_at,
    processedAt: source.processed_at,
    deletedAt: source.deleted_at,
  }
}

export async function listSources(workspaceId: number): Promise<SourceData[]> {
  const sources = await apiFetch<SourceDataApi[]>(`/sources?workspace_id=${workspaceId}`)
  return sources.map(fromApi)
}

export async function getSource(sourceId: number): Promise<SourceData> {
  return fromApi(await apiFetch<SourceDataApi>(`/sources/${sourceId}`))
}

export async function createSource(input: CreateSourceInput): Promise<SourceData> {
  const formData = new FormData()
  formData.append('workspace_id', String(input.workspaceId))
  formData.append('title', input.title)
  formData.append('file', input.file)
  formData.append('team_label', input.teamLabel)
  for (const cat of input.categoryLabels) {
    formData.append('category_labels', cat)
  }
  if (input.periodStart) formData.append('period_start', input.periodStart)
  if (input.periodEnd) formData.append('period_end', input.periodEnd)
  if (input.periodLabel) formData.append('period_label', input.periodLabel)

  return fromApi(
    await apiFetch<SourceDataApi>('/sources', {
      method: 'POST',
      body: formData,
    }),
  )
}

export async function deleteSource(sourceId: number): Promise<void> {
  return apiFetch<void>(`/sources/${sourceId}`, {
    method: 'DELETE',
  })
}

export async function retrySource(sourceId: number): Promise<SourceData> {
  return fromApi(
    await apiFetch<SourceDataApi>(`/sources/${sourceId}/retry-processing`, {
      method: 'POST',
    }),
  )
}
