import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function CommandResultMessage({ content }: { content: string }) {
  return (
    <article className="prose-chat rounded-2xl border border-border/70 bg-surface-subtle/70 p-5 text-sm leading-7 text-foreground">
      <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
    </article>
  )
}
