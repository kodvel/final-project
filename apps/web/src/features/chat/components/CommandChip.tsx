export function CommandChip({ command, label, onClick }: { command: string; label: string; onClick?: () => void }) {
  const content = (
    <>
      <span className="rounded bg-chip-gray px-2 py-1 font-mono text-text-hint">{command}</span> {label}
    </>
  )
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className="inline-flex items-center gap-1 transition hover:text-foreground">
        {content}
      </button>
    )
  }
  return <span>{content}</span>
}
