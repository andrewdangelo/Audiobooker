/**
 * StoreBookGrid Component
 * 
 * Displays a responsive grid of audiobooks available in the store.
 * Uses Redux for state management and supports filtering/sorting.
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - Responsive grid layout (2-6 columns based on screen size)
 * - Loading skeleton states
 * - Empty state handling
 * - Integrated with Redux store state
 * 
 * USAGE:
 * ```tsx
 * // Basic usage - uses Redux filtered books
 * <StoreBookGrid />
 * 
 * // With section title
 * <StoreBookGrid title="Featured Books" books={featuredBooks} />
 * ```
 * 
 * API INTEGRATION:
 * - This component reads from Redux store (selectFilteredStoreBooks)
 * - Parent component should dispatch fetchStoreBooks on mount
 */

import StoreBookCard from './StoreBookCard'
import { useAppSelector, useAppDispatch } from '@/store'
import { 
  selectFilteredStoreBooks, 
  selectUserCredits,
  purchaseBook,
  type StoreBook 
} from '@/store/slices/storeSlice'
import { Loader2, PackageOpen } from 'lucide-react'
import { cn } from '@/lib/utils'

// ============================================================================
// TYPES
// ============================================================================

interface StoreBookGridProps {
  /** Optional title for the grid section */
  title?: string
  /** Optional subtitle/description */
  subtitle?: string
  /** Override books to display (instead of using Redux filtered state) */
  books?: StoreBook[]
  /** Loading state override */
  loading?: boolean
  /** Maximum number of books to display (for featured sections) */
  limit?: number
  /** Number of columns on large screens (default: 5) */
  columns?: 3 | 4 | 5 | 6
  /** Additional class names */
  className?: string
  /** Show empty state when no books */
  showEmptyState?: boolean
}

// ============================================================================
// LOADING SKELETON
// ============================================================================

/**
 * Skeleton loading card for smooth loading experience
 * Matches the height structure of StoreBookCard for consistent layout
 */
function StoreBookCardSkeleton() {
  return (
    <div className="animate-pulse flex flex-col">
      {/* Cover Image Skeleton */}
      <div className="aspect-[3/4] bg-muted rounded-t-xl flex-shrink-0" />
      {/* Content Skeleton - Fixed height to match StoreBookCard */}
      <div className="p-3 space-y-2 border border-t-0 rounded-b-xl h-[140px] flex flex-col">
        <div className="h-4 bg-muted rounded w-3/4" />
        <div className="h-4 bg-muted rounded w-full" />
        <div className="h-3 bg-muted rounded w-1/2" />
        <div className="h-3 bg-muted rounded w-2/3" />
        <div className="flex justify-between pt-1 border-t border-border/50 mt-auto">
          <div className="h-4 bg-muted rounded w-16" />
          <div className="h-4 bg-muted rounded w-12" />
        </div>
      </div>
    </div>
  )
}

/**
 * Loading skeleton grid
 */
function LoadingSkeleton({ count = 8 }: { count?: number }) {
  return (
    <>
      {[...Array(count)].map((_, i) => (
        <StoreBookCardSkeleton key={i} />
      ))}
    </>
  )
}

// ============================================================================
// EMPTY STATE
// ============================================================================

/**
 * Empty state when no books match filters
 */
function EmptyState() {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
      <PackageOpen className="h-16 w-16 text-muted-foreground/50 mb-4" />
      <h3 className="text-lg font-semibold text-muted-foreground">
        No audiobooks found
      </h3>
      <p className="text-sm text-muted-foreground/70 mt-1 max-w-md">
        Try adjusting your search or filters to find what you're looking for.
      </p>
    </div>
  )
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function StoreBookGrid({
  title,
  subtitle,
  books: propBooks,
  loading = false,
  limit,
  columns = 5,
  className,
  showEmptyState = true,
}: StoreBookGridProps) {
  const dispatch = useAppDispatch()
  
  // Get books from Redux if not provided via props
  const reduxBooks = useAppSelector(selectFilteredStoreBooks)
  const userCredits = useAppSelector(selectUserCredits)
  
  // Use prop books if provided, otherwise use Redux filtered books
  let books = propBooks ?? reduxBooks
  
  // Apply limit if specified
  if (limit && books.length > limit) {
    books = books.slice(0, limit)
  }

  /**
   * Handle add to cart action
   * 
   * TODO: API INTEGRATION
   * Connect to your cart service:
   * - dispatch(addToCart(bookId))
   * - Show toast notification
   */
  const handleAddToCart = (bookId: string) => {
    console.log('Add to cart:', bookId)
    // TODO: Implement cart functionality
    // dispatch(addToCart(bookId))
  }

  /**
   * Handle buy with credits action
   * 
   * TODO: API INTEGRATION
   * Connect to your purchase service:
   * - dispatch(purchaseBook({ bookId, useCredits: true }))
   * - Show confirmation modal
   * - Handle success/error states
   */
  const handleBuyWithCredits = (bookId: string) => {
    console.log('Buy with credits:', bookId)
    // Dispatch purchase action
    dispatch(purchaseBook({ bookId, useCredits: true }))
  }

  // Determine grid column classes based on columns prop
  const gridCols = {
    3: 'grid-cols-2 sm:grid-cols-2 md:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
    5: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5',
    6: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6',
  }

  return (
    <section className={cn("space-y-4", className)}>
      {/* Section Header */}
      {(title || subtitle) && (
        <div className="space-y-1">
          {title && (
            <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
          )}
          {subtitle && (
            <p className="text-muted-foreground">{subtitle}</p>
          )}
        </div>
      )}

      {/* Grid Container */}
      <div className={cn("grid gap-4", gridCols[columns])}>
        {/* Loading State */}
        {loading && <LoadingSkeleton count={limit ?? 10} />}

        {/* Empty State */}
        {!loading && books.length === 0 && showEmptyState && <EmptyState />}

        {/* Book Cards */}
        {!loading &&
          books.map((book) => (
            <StoreBookCard
              key={book.id}
              book={book}
              onAddToCart={handleAddToCart}
              onBuyWithCredits={handleBuyWithCredits}
              hasEnoughCredits={userCredits >= book.credits}
            />
          ))}
      </div>

      {/* Loading indicator for infinite scroll (if needed later) */}
      {loading && books.length > 0 && (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}
    </section>
  )
}
