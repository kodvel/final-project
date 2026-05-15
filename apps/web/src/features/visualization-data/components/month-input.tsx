import { useId } from 'react'
import { Input } from '../../../components/ui/input'

export function MonthInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const inputId = useId()

  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={inputId} className="text-[11px] font-medium text-muted-foreground">
        {label}
      </label>
      <Input
        id={inputId}
        type="month"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full min-w-0 border-border bg-white shadow-sm transition placeholder:text-muted-foreground/60 focus-visible:ring-primary/20"
      />
    </div>
  )
}
