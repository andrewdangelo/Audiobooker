/**
 * Tooltip Component
 * 
 * Simple tooltip component for displaying hints on hover.
 */

import * as React from "react"

interface TooltipProps {
  children: React.ReactNode
  content: string
  side?: 'top' | 'right' | 'bottom' | 'left'
  delayDuration?: number
}

export function Tooltip({ children, content, side = 'right', delayDuration = 200 }: TooltipProps) {
  const [isVisible, setIsVisible] = React.useState(false)
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  
  const showTooltip = () => {
    timeoutRef.current = setTimeout(() => setIsVisible(true), delayDuration)
  }
  
  const hideTooltip = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setIsVisible(false)
  }
  
  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2'
  }
  
  return (
    <div 
      className="relative inline-flex"
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}
      {isVisible && (
        <div
          role="tooltip"
          className={`absolute z-50 px-2 py-1 text-xs font-medium text-popover-foreground bg-popover border rounded-md shadow-md whitespace-nowrap animate-in fade-in-0 zoom-in-95 ${positionClasses[side]}`}
        >
          {content}
        </div>
      )}
    </div>
  )
}

export default Tooltip
