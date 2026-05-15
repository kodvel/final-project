import { Bot, ExternalLink } from 'lucide-react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { AgentToolCall, MessageSourceCitation } from '../../../types/chat'
import { EvidenceChip } from './EvidenceChip'
import { ProcessPill } from './ProcessPill'
import { isOptimistic, type DisplayMessage, type StreamingToolCall } from './types'
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
    <article className="max-w-[min(52rem,100%)] motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300">
      <div className="relative">
        <div>
          <header className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-accent text-primary ring-1 ring-primary/10">
              <Bot className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <h2 className="font-heading text-[15px] font-semibold leading-5 text-foreground">Intelligence Copilot</h2>
              <p className="mt-1 text-xs text-text-hint">Strategic consultant · Source-grounded response</p>
            </div>
          </header>

          {(showThinking || processItems.length > 0) && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {showThinking && processItems.length === 0 && <ProcessPill label="Thinking…" status="running" />}
              {processItems.map((item) => (
                <ProcessPill key={item.id} label={item.label} status={item.status} />
              ))}
            </div>
          )}

          {message.content && (
            <div className="prose-chat mt-4 text-[15px] leading-8 text-foreground/95">
              <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
            </div>
          )}

          {message.content.length > 0 && citations.length > 0 && (
            <section className="mt-5 rounded-2xl bg-surface-subtle/70 p-4">
              <p className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-hint">Evidence</p>
              <div className="flex flex-wrap gap-2">
                {citations.map((citation) => (
                  <EvidenceChip key={citation.id} citation={citation} />
                ))}
              </div>
            </section>
          )}

          <TraceLink message={message} />
        </div>
      </div>
    </article>
  )
}

function TraceLink({ message }: { message: DisplayMessage }) {
  if (isOptimistic(message)) return null
  const url = message.traceUrl
  if (!url) return null
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-4 inline-flex items-center gap-1.5 text-xs text-text-hint hover:text-primary transition-colors"
      title="Open trace in Langfuse"
    >
      <ExternalLink className="h-3.5 w-3.5" />
      View trace
    </a>
  )
}
