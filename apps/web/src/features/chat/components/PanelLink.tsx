import { ChevronRight } from 'lucide-react'

export function PanelLink({ label }: { label: string }) {
  return (
    <button className="flex w-full items-center justify-between py-3 text-sm font-medium text-foreground hover:text-primary" type="button">
      {label}
      <ChevronRight className="h-4 w-4" />
    </button>
  )
}
