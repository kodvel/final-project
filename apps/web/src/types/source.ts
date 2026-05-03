import type { CategoryLabel, IsoDateTime, ProcessingStatus, SourceFileType, TeamLabel } from './common'

export type SourceData = {
  id: number
  workspaceId: number
  title: string
  teamLabel: TeamLabel
  categoryLabels: CategoryLabel[]
  fileType: SourceFileType
  originalFilename: string
  periodStart?: IsoDateTime | null
  periodEnd?: IsoDateTime | null
  periodLabel?: string | null
  processingStatus: ProcessingStatus
  uploadedAt: IsoDateTime
}
