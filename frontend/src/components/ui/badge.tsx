/**
 * Badge Component
 * 
 * A versatile badge/chip component for displaying status, tags, 
 * genres, and other metadata throughout the application.
 * 
 * @example
 * // Default badge
 * <Badge>Fiction</Badge>
 * 
 * // Sale badge (destructive variant)
 * <Badge variant="destructive">SALE</Badge>
 * 
 * // Credit badge with outline
 * <Badge variant="outline">1 Credit</Badge>
 */

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * Badge variants using class-variance-authority (cva)
 * Provides consistent styling across different badge types
 */
const badgeVariants = cva(
  // Base styles applied to all badges
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        // Default: Primary colored badge
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        // Secondary: Muted, less prominent badge
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        // Destructive: Error/warning states, sale badges
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        // Outline: Bordered badge with transparent background
        outline: "text-foreground",
        // Success: Positive states (completed, available)
        success:
          "border-transparent bg-green-500/15 text-green-600 dark:text-green-400",
        // Warning: Attention-grabbing (limited time offers)
        warning:
          "border-transparent bg-yellow-500/15 text-yellow-600 dark:text-yellow-400",
        // Info: Informational badges
        info:
          "border-transparent bg-blue-500/15 text-blue-600 dark:text-blue-400",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        sm: "px-2 py-0.5 text-[10px]",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

/**
 * Badge component for displaying short labels and status indicators
 * 
 * @param variant - Visual style variant (default, secondary, destructive, outline, success, warning, info)
 * @param size - Size variant (default, sm, lg)
 * @param className - Additional CSS classes
 */
function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
