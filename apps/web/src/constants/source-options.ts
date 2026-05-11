import type { CategoryLabel, ProcessingStatus, SourceFileType, TeamLabel } from '../types/common'

type SourceOption<T extends string> = {
  value: T
  label: string
}

export const TEAM_LABEL_OPTIONS = [
  { value: 'marketing', label: 'Marketing' },
  { value: 'product', label: 'Product' },
  { value: 'data_analysis', label: 'Data Analysis' },
  { value: 'business', label: 'Business' },
] satisfies Array<SourceOption<TeamLabel>>

export const CATEGORY_LABEL_OPTIONS = [
  { value: 'analytics_metrics', label: 'Analytics / Metrics' },
  { value: 'market_research', label: 'Market Research' },
  { value: 'product_feature', label: 'Product / Feature' },
  { value: 'customer_insight', label: 'Customer Insight' },
  { value: 'business_model', label: 'Business Model' },
  { value: 'competitor_analysis', label: 'Competitor Analysis' },
  { value: 'revenue_sales', label: 'Revenue / Sales' },
] satisfies Array<SourceOption<CategoryLabel>>

export const SOURCE_FILE_TYPE_OPTIONS = [
  { value: 'csv', label: 'CSV' },
  { value: 'pdf', label: 'PDF' },
] satisfies Array<SourceOption<SourceFileType>>

export const PROCESSING_STATUS_OPTIONS = [
  { value: 'ready', label: 'Ready' },
  { value: 'processing', label: 'Processing' },
  { value: 'uploaded', label: 'Uploaded' },
  { value: 'failed', label: 'Failed' },
] satisfies Array<SourceOption<ProcessingStatus>>

export const TEAM_LABEL_VALUES = TEAM_LABEL_OPTIONS.map((option) => option.value)
export const CATEGORY_LABEL_VALUES = CATEGORY_LABEL_OPTIONS.map((option) => option.value)

const SOURCE_OPTION_LABELS = new Map<string, string>(
  [...TEAM_LABEL_OPTIONS, ...CATEGORY_LABEL_OPTIONS, ...SOURCE_FILE_TYPE_OPTIONS, ...PROCESSING_STATUS_OPTIONS].map((option) => [
    option.value,
    option.label,
  ]),
)

export function formatSourceOptionLabel(value: string): string {
  return SOURCE_OPTION_LABELS.get(value) ?? value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}
