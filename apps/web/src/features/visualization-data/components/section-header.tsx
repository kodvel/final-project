import type { ReactNode } from 'react'

export function SectionHeader({ eyebrow, title, description, icon }: { eyebrow: string; title: string; description: string; icon?: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      {icon ? <div className="mt-0.5 rounded-full bg-primary/10 p-2 text-primary">{icon}</div> : null}
      <div>
        <p className="text-xs font-medium text-muted-foreground">{eyebrow}</p>
        <h2 className="mt-1 font-heading text-lg font-semibold text-foreground">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
