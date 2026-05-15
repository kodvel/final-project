export function getDefaultMonthRange() {
  const now = new Date()

  return {
    start: toMonthInputValue(new Date(now.getFullYear(), now.getMonth() - 5, 1)),
    end: toMonthInputValue(now),
  }
}

export function toMonthInputValue(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

export function formatMonthRange(startMonth: string, endMonth: string) {
  return startMonth && endMonth ? `${startMonth} → ${endMonth}` : 'Select a month range'
}

export function formatTimestamp(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function formatLabel(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function formatConfidence(value: import('../../types/visualization').VisualizationSnapshotListItem['confidence']) {
  if (typeof value === 'number') return `${Math.round(value * 100)}%`
  return String(value).toUpperCase()
}

export function confidenceColorClass(value: string): string {
  const upper = value.toUpperCase()
  if (upper === 'HIGH') return 'border-emerald-200 bg-emerald-50 text-emerald-500'
  if (upper === 'MEDIUM') return 'border-amber-200 bg-amber-50 text-amber-500'
  if (upper === 'LOW') return 'border-rose-200 bg-rose-50 text-rose-500'
  return ''
}

export function itemKey(item: import('../../types/visualization').VisualizationSnapshotListItem) {
  return [item.kind, item.theme ?? '', item.title ?? item.text ?? item.detail ?? item.description ?? 'item', item.confidence ?? ''].join('|')
}

export function evidenceRefKey(ref: import('../../types/visualization').VisualizationEvidenceRef) {
  return [ref.sourceId ?? '', ref.artifactId ?? '', ref.sourceTitle ?? '', ref.pageNumber ?? '', ref.quote ?? ''].join('|')
}

export function uniqueLabels(values: string[]) {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b))
}

export type ChartPoint = {
  label: string
  actual: number
  baseline: number
}

export function buildChartSeries(
  startMonth: string,
  endMonth: string,
  { sourceCount, patternCount, gapCount, expanded }: { sourceCount: number; patternCount: number; gapCount: number; expanded: boolean },
): ChartPoint[] {
  const months = enumerateMonths(startMonth, endMonth)
  const limit = expanded ? 8 : 6
  const sampled = months.length > limit ? sampleMonths(months, limit) : months
  const baselineBias = Math.max(4, patternCount * 1.5 - gapCount)

  return sampled.map((date, index) => {
    const seasonalWave = Math.sin((index / Math.max(sampled.length - 1, 1)) * Math.PI) * 12
    const drift = index * 1.8
    const actual = clamp(38 + sourceCount * 1.6 + seasonalWave + drift + patternCount * 2.5 - gapCount * 1.3, 24, 92)
    const baseline = clamp(actual - baselineBias + (index % 2 === 0 ? 2.5 : -1.5), 18, 88)

    return {
      label: new Intl.DateTimeFormat('en', { month: 'short' }).format(date),
      actual,
      baseline,
    }
  })
}

function enumerateMonths(startMonth: string, endMonth: string) {
  if (!startMonth || !endMonth) return []

  const [startYear, startMonthIndex] = startMonth.split('-').map(Number)
  const [endYear, endMonthIndex] = endMonth.split('-').map(Number)
  const start = new Date(startYear, startMonthIndex - 1, 1)
  const end = new Date(endYear, endMonthIndex - 1, 1)
  const months: Date[] = []

  const cursor = new Date(start)
  while (cursor <= end) {
    months.push(new Date(cursor))
    cursor.setMonth(cursor.getMonth() + 1)
  }

  return months
}

function sampleMonths(months: Date[], limit: number) {
  if (months.length <= limit) return months

  return Array.from({ length: limit }, (_, index) => months[Math.round((index * (months.length - 1)) / (limit - 1))])
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}
