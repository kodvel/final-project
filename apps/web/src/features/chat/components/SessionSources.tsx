import type { AgentToolCall, MessageSourceCitation } from '../../../types/chat'
import { SourceGroupCard } from './SourceGroupCard'
import { groupCitations } from './utils'

export function SessionSources({ citations, toolCalls }: { citations: MessageSourceCitation[]; toolCalls: AgentToolCall[] }) {
  const uploadedCitations = citations.filter((c) => c.citationType === 'uploaded_source')
  const webCitations = citations.filter((c) => c.citationType === 'web')
  const uploadedGroups = groupCitations(uploadedCitations)
  const webGroups = groupCitations(webCitations)

  return (
    <div className="space-y-4">
      {uploadedCitations.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Uploaded Sources</p>
          <div className="space-y-3">
            {uploadedGroups.map((group) => (
              <SourceGroupCard key={group.key} group={group} type={group.title.toLowerCase().endsWith('.pdf') ? 'pdf' : 'csv'} />
            ))}
          </div>
        </div>
      )}

      {webCitations.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Web Sources</p>
          <div className="space-y-3">
            {webGroups.map((group) => (
              <SourceGroupCard key={group.key} group={group} type="web" />
            ))}
          </div>
        </div>
      )}

      {toolCalls.length > 0 && (
        <div>
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-text-hint">Tool Calls</p>
          <div className="space-y-2">
            {toolCalls.map((tc) => (
              <div key={tc.id} className="rounded-lg border border-border bg-card px-4 py-3 text-xs text-muted-foreground shadow-sm">
                <span className="font-mono uppercase tracking-[0.12em] text-text-hint">{tc.status}</span>{' '}
                <span className="font-semibold text-foreground">{tc.toolName}</span>
                {tc.summary && <span className="ml-1">— {tc.summary}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
