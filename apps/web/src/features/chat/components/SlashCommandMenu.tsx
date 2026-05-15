import { useEffect, useRef } from 'react'

// ---------------------------------------------------------------------------
// Command registry
// ---------------------------------------------------------------------------

export type SlashCommand = {
  command: string
  label: string
  description: string
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    command: '/decision-brief',
    label: 'Decision Brief',
    description: 'Generate a strategic decision brief draft',
  },
]

export function filterCommands(query: string): SlashCommand[] {
  if (!query.startsWith('/')) return []
  const prefix = query.toLowerCase()
  return SLASH_COMMANDS.filter((cmd) => cmd.command.startsWith(prefix))
}

// ---------------------------------------------------------------------------
// Menu component
// ---------------------------------------------------------------------------

type SlashCommandMenuProps = {
  commands: SlashCommand[]
  activeIndex: number
  onSelect: (command: SlashCommand) => void
  onClose: () => void
}

export function SlashCommandMenu({ commands, activeIndex, onSelect }: SlashCommandMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)

  // Scroll active item into view
  useEffect(() => {
    const menu = menuRef.current
    if (!menu) return
    const active = menu.children[activeIndex] as HTMLElement | undefined
    active?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  if (commands.length === 0) return null

  return (
    <div
      ref={menuRef}
      id="slash-command-menu"
      role="listbox"
      aria-label="Slash commands"
      className="absolute bottom-full left-0 right-0 z-50 mb-2 overflow-hidden rounded-xl border border-border/70 bg-white shadow-[0_8px_28px_rgba(15,23,42,0.12)]"
    >
      <div className="px-3 pt-2.5 pb-1">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-text-hint">Commands</p>
      </div>
      {commands.map((cmd, index) => (
        <button
          key={cmd.command}
          type="button"
          role="option"
          aria-selected={index === activeIndex}
          onClick={() => onSelect(cmd)}
          className={`flex w-full items-center gap-3 px-3 py-2.5 text-left transition ${
            index === activeIndex
              ? 'bg-primary/5 text-primary'
              : 'text-foreground hover:bg-surface-subtle'
          }`}
        >
          <span className="shrink-0 rounded-md bg-chip-gray px-2 py-1 font-mono text-xs text-text-hint">
            {cmd.command}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-medium">{cmd.label}</span>
            <span className="block text-xs text-text-hint">{cmd.description}</span>
          </span>
        </button>
      ))}
    </div>
  )
}
