// TODO: Implement Progress component using shadcn/ui
// This is a placeholder - use: npx shadcn-ui@latest add progress

import * as React from "react"

interface ProgressProps {
  value?: number
  className?: string
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ value = 0, className }, ref) => {
    return (
      <div ref={ref} className={className}>
        <div style={{ width: `${value}%` }} />
      </div>
    )
  }
)
Progress.displayName = "Progress"

export { Progress }
