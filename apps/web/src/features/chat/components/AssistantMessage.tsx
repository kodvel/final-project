import { Bot } from 'lucide-react'
import type { AgentToolCall, MessageSourceCitation } from '../../../types/chat'
import { EvidenceChip } from './EvidenceChip'
import { ProcessPill } from './ProcessPill'
import { TraceLink } from './TraceLink'
import type { DisplayMessage, StreamingToolCall } from './types'
import { processLabelForTool } from './utils'

export function AssistantMessage({
  message,
  citations,
  toolCalls,
  streamingToolCalls,
  showThinking,
}: {
  message: DisplayMessage
  citations: MessageSourceCitation[]
  toolCalls: AgentToolCall[]
  streamingToolCalls: StreamingToolCall[]
  showThinking: boolean
}) {
  const processItems = [
    ...streamingToolCalls.map((tool) => ({ id: tool.callId, label: processLabelForTool(tool.toolName), status: tool.status })),
    ...toolCalls.map((toolCall) => ({
      id: String(toolCall.id),
      label: processLabelForTool(toolCall.toolName),
      status: toolCall.status === 'failed' ? 'failed' : toolCall.status === 'running' ? 'running' : 'done',
    })),
  ]

  return (
    <article className="space-y-3 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-hint">
        <Bot className="h-4 w-4 text-primary" />
        Intelligence Copilot
      </div>

      {(showThinking || processItems.length > 0) && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {showThinking && processItems.length === 0 && <ProcessPill label="Thinking…" status="running" />}
          {processItems.map((item) => (
            <ProcessPill key={item.id} label={item.label} status={item.status} />
          ))}
        </div>
      )}

      {message.content && <p className="whitespace-pre-line text-[15px] leading-8 text-foreground">{message.content}</p>}

      {message.content.length > 0 && citations.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {citations.map((citation) => (
            <EvidenceChip key={citation.id} citation={citation} />
          ))}
        </div>
      )}

      <TraceLink message={message} />
    </article>
  )
}
