import type { CategoryLabel, TeamLabel } from './common'

export type VisualizationArtifactType = 'csv_profile' | 'chart_spec' | 'insight_card' | 'source_summary' | 'source_insight'

export type VisualizationArtifact = {
  id: number
  sourceId: number
  artifactType: VisualizationArtifactType
  title: string
  contentJson: VisualizationArtifactContent
  // Optional source metadata when included by the API
  sourceTitle?: string
  sourceFileType?: 'csv' | 'pdf'
  teamLabel?: TeamLabel
  categoryLabels?: CategoryLabel[]
}

export type VisualizationArtifactApi = {
  id: number
  source_id: number
  artifact_type: VisualizationArtifactType
  title: string
  content_json: Record<string, unknown>
  // Extended response shape includes source metadata
  source_title?: string
  source_file_type?: 'csv' | 'pdf'
  team_label?: TeamLabel
  category_labels?: CategoryLabel[]
}

// CSV Profile content
export type CsvProfileContent = {
  total_rows: number
  total_columns: number
  columns: Array<{
    name: string
    type: 'numeric' | 'categorical' | 'date' | 'text'
    null_count: number
    unique_count: number
    min?: string | number
    max?: string | number
    sample_values?: string[]
  }>
  summary?: {
    numeric_columns: string[]
    categorical_columns: string[]
    date_columns: string[]
  }
}

// Chart spec content
export type ChartSpecContent = {
  chart_type: 'bar' | 'line' | 'scatter' | 'area' | 'combo'
  title: string
  x_axis: string
  y_axis: string
  y_axis_2?: string
  description?: string
  kpis?: Array<{
    label: string
    value: string
    delta?: string
    trend?: 'up' | 'down'
  }>
  data_points?: Array<{
    label: string
    values: number[]
  }>
  insights?: string[]
}

// Insight card content
export type InsightCardContent = {
  insight_type: 'anomaly' | 'trend' | 'risk' | 'opportunity' | 'summary'
  title: string
  description: string
  confidence?: number
  evidence?: string[]
  recommendation?: string
}

// Citation-ready object used in source_insight arrays
export type CitationItem = {
  text?: string
  quote?: string
  page_number?: number | null
}

// Source insight content for Document Insight
export type SourceInsightContent = {
  key_findings: Array<string | CitationItem>
  assumptions?: Array<string | CitationItem>
  risks: Array<string | CitationItem>
  opportunities: Array<string | CitationItem>
  source_quotes?: Array<string | CitationItem>
}

// Source summary content for Document Insight
export type SourceSummaryContent = {
  summary: string
  page_count?: number
  ocr_model?: string
  structuring_model?: string
  extracted_markdown_path?: string
  chunk_metadata_path?: string
  warnings?: string[]
}

// Union type for artifact content
export type VisualizationArtifactContent =
  | CsvProfileContent
  | ChartSpecContent
  | InsightCardContent
  | SourceSummaryContent
  | SourceInsightContent
  | Record<string, unknown>

// Artifact grouped by source for list view
export type VisualizationSourceGroup = {
  sourceId: number
  sourceTitle: string
  sourceFileType: 'csv' | 'pdf'
  teamLabel?: TeamLabel
  categoryLabels?: CategoryLabel[]
  artifacts: VisualizationArtifact[]
}

// Filter params for list endpoint
export type VisualizationFilters = {
  workspaceId: number
  teamLabel?: TeamLabel
  categoryLabel?: CategoryLabel
  periodStart?: string
  periodEnd?: string
}
