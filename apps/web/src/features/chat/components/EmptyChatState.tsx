export function EmptyChatState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-muted bg-surface-subtle p-8 text-center">
      <h2 className="font-heading text-lg font-semibold text-foreground">{title}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  )
}
