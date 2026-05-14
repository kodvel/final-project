export function CommandResultMessage({ content }: { content: string }) {
  return (
    <article className="rounded-2xl border border-dashed border-border bg-surface-subtle p-5 text-sm leading-7 text-foreground whitespace-pre-line">
      {content}
    </article>
  )
}
