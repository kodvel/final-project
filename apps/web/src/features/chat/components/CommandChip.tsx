export function CommandChip({ command, label, onClick }: { command: string; label: string; onClick?: () => void }) {
  const content = (
    <>
      <span className="rounded-full bg-chip-gray px-2.5 py-1 font-mono text-[11px] text-text-hint">{command}</span> {label}
    </>
  )
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1.5 rounded-full border border-transparent px-2 py-1 text-left font-medium text-foreground transition hover:border-primary/10 hover:bg-surface-subtle hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
      >
        {content}
      </button>
    )
  }
  return <span>{content}</span>
}
