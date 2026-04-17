import * as React from 'react'

import { cn } from '@/lib/utils'

interface ProgressProps {
  value?: number
  className?: string
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ value = 0, className }, ref) => {
    const safeValue = Math.max(0, Math.min(100, value))

    return (
      <div
        ref={ref}
        className={cn('h-2 w-full overflow-hidden rounded-full bg-muted', className)}
      >
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${safeValue}%` }}
        />
      </div>
    )
  },
)

Progress.displayName = 'Progress'

export { Progress }
