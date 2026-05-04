import type { CategoryLabel, IsoDateTime, ProcessingStatus, SourceFileType, TeamLabel } from './common'

export type SourceData = {
  id: number
  workspaceId: number
  title: string
  teamLabel: TeamLabel
  categoryLabels: CategoryLabel[]
  fileType: SourceFileType
  originalFilename: string
  storagePath?: string
  periodStart?: IsoDateTime | null
  periodEnd?: IsoDateTime | null
  periodLabel?: string | null
  processingStatus: ProcessingStatus
  processingError?: string | null
  uploadedAt: IsoDateTime
  processedAt?: IsoDateTime | null
  deletedAt?: IsoDateTime | null
}

export type CreateSourceInput = {
  workspaceId: number
  title: string
  file: File
  teamLabel: TeamLabel
  categoryLabels: CategoryLabel[]
  periodStart?: string
  periodEnd?: string
  periodLabel?: string
}

export type SourceDataApi = {
  id: number
  workspace_id: number
  title: string
  team_label: TeamLabel
  category_labels: CategoryLabel[]
  file_type: SourceFileType
  original_filename: string
  storage_path: string
  period_start?: IsoDateTime | null
  period_end?: IsoDateTime | null
  period_label?: string | null
  processing_status: ProcessingStatus
  processing_error?: string | null
  uploaded_at: IsoDateTime
  processed_at?: IsoDateTime | null
  deleted_at?: IsoDateTime | null
}

export type SourceSummary = {
  total: number
  processing: number
  ready: number
  failed: number
}
