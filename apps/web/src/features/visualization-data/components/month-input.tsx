import { useState } from 'react'
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '../../../components/ui/popover'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function parseMonthValue(value: string): { year: number; month: number } | null {
  const match = value.match(/^(\d{4})-(\d{2})$/)
  if (!match) return null
  return { year: Number(match[1]), month: Number(match[2]) }
}

export function MonthInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const parsed = parseMonthValue(value)
  const [viewYear, setViewYear] = useState(() => parsed?.year ?? new Date().getFullYear())
  const [open, setOpen] = useState(false)

  function handleSelect(month: number) {
    onChange(`${viewYear}-${String(month).padStart(2, '0')}`)
    setOpen(false)
  }

  const displayLabel = parsed
    ? `${MONTHS[parsed.month - 1]} ${parsed.year}`
    : 'Select month'

  return (
    <div className="flex min-w-0 flex-col gap-1.5 w-fit">
      <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="w-[140px] justify-between border-border bg-white shadow-sm text-sm font-normal"
          >
            <span className={parsed ? 'text-foreground' : 'text-muted-foreground'}>{displayLabel}</span>
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[220px] p-3" align="start">
          <div className="flex items-center justify-between mb-3">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setViewYear((y) => y - 1)}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm font-semibold">{viewYear}</span>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setViewYear((y) => y + 1)}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="grid grid-cols-3 gap-1">
            {MONTHS.map((name, index) => {
              const monthNum = index + 1
              const isSelected = parsed?.year === viewYear && parsed?.month === monthNum
              return (
                <Button
                  key={name}
                  variant={isSelected ? 'default' : 'ghost'}
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => handleSelect(monthNum)}
                >
                  {name}
                </Button>
              )
            })}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
