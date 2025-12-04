/**
 * Checkbox Component
 * 
 * Accessible checkbox component with custom styling.
 */

import * as React from "react"

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className = "", id, label, ...props }, ref) => {
    return (
      <div className="flex items-center">
        <input
          type="checkbox"
          ref={ref}
          id={id}
          className={`h-4 w-4 rounded border border-input bg-background text-primary 
            focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 
            disabled:cursor-not-allowed disabled:opacity-50 
            accent-primary cursor-pointer ${className}`}
          {...props}
        />
        {label && (
          <label 
            htmlFor={id} 
            className="ml-2 text-sm text-muted-foreground cursor-pointer select-none"
          >
            {label}
          </label>
        )}
      </div>
    )
  }
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
