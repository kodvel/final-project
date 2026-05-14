import { ExternalLink } from 'lucide-react'
import type { DisplayMessage } from './types'
import { isOptimistic } from './types'

export function TraceLink({ message }: { message: DisplayMessage }) {
  if (isOptimistic(message)) return null
  const url = message.traceUrl
  if (!url) return null
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-xs text-text-hint hover:text-primary transition-colors"
      title="Open trace in Langfuse"
    >
      <ExternalLink className="h-3.5 w-3.5" />
      View trace
    </a>
  )
}
