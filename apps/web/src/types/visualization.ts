import type { CategoryLabel, IsoDateTime, TeamLabel } from './common'

export type VisualizationEvidenceRef = {
  sourceId?: number
  sourceTitle?: string
  artifactId?: number
  quote?: string
  pageNumber?: number | null
}

export type VisualizationCoverageSection = {
  totalSources?: number
  readySources?: number
  excludedSources?: number
  summary?: string
  notes?: string[]
}

export type VisualizationSourceCard = {
  sourceId: number
  title: string
  summary?: string
  sourceFileType?: 'csv' | 'pdf'
  teamLabel?: TeamLabel
  categoryLabels?: CategoryLabel[]
  periodLabel?: string | null
  evidenceRefs?: VisualizationEvidenceRef[]
}

export type VisualizationSnapshotListItem = {
  title?: string
  text?: string
  detail?: string
  description?: string
  kind?: 'finding' | 'risk' | 'assumption' | 'opportunity' | 'gap'
  confidence?: number
  evidenceRefs?: VisualizationEvidenceRef[]
}

export type VisualizationRiskAssumptionItem = VisualizationSnapshotListItem & {
  kind?: 'risk' | 'assumption'
}

export type VisualizationSnapshotContent = {
  coverage: VisualizationCoverageSection
  source_cards: VisualizationSourceCard[]
  key_findings: VisualizationSnapshotListItem[]
  risks_assumptions: VisualizationRiskAssumptionItem[]
  opportunities: VisualizationSnapshotListItem[]
  gaps: VisualizationSnapshotListItem[]
}

export type VisualizationSnapshotApi = {
  id: number
  workspace_id: number
  period_start_month: string
  period_end_month: string
  content_json: VisualizationSnapshotContent
  source_ids_json?: number[]
  artifact_ids_json?: number[]
  status?: string
  generation_error?: string | null
  generated_at?: IsoDateTime | null
  updated_at?: IsoDateTime | null
}

export type VisualizationSnapshot = {
  id: number
  workspaceId: number
  periodStartMonth: string
  periodEndMonth: string
  contentJson: VisualizationSnapshotContent
  sourceIds?: number[]
  artifactIds?: number[]
  status?: string
  generationError?: string | null
  generatedAt?: IsoDateTime | null
  updatedAt?: IsoDateTime | null
}

export type VisualizationSnapshotQueryParams = {
  workspaceId: number
  periodStartMonth: string
  periodEndMonth: string
}
