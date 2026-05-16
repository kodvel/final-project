import type { MessageSourceCitation } from '../../../types/chat'
import type { CitationGroup } from './types'

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function processLabelForTool(toolName: string) {
  if (toolName === 'retrieve_company_knowledge') return 'Searching company Sources…'
  if (toolName === 'tavily_web_search') return 'Searching web…'
  if (toolName === 'list_sources') return 'Listing data sources…'
  if (toolName === 'execute_python') return 'Running code analysis…'
  return 'Using tool…'
}

export function groupCitations(citations: MessageSourceCitation[]): CitationGroup[] {
  const groups = new Map<string, CitationGroup>()
  for (const citation of citations) {
    const key =
      citation.citationType === 'web'
        ? citation.url || citation.domain || citation.title || `web-${citation.id}`
        : String(citation.sourceId ?? citation.title ?? citation.id)
    const title =
      citation.citationType === 'web'
        ? citation.title || citation.domain || 'Web Source'
        : citation.title || `Source #${citation.sourceId ?? 'unknown'}`
    const badge = citation.citationType === 'web' ? 'Web' : citation.citationStatus === 'available' ? 'Uploaded' : citation.citationStatus
    const group = groups.get(key)
    if (group) {
      group.citations.push(citation)
    } else {
      groups.set(key, { key, title, badge, citations: [citation] })
    }
  }
  return Array.from(groups.values())
}
