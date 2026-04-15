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

import { useState } from 'react'
import StoreBookCard from './StoreBookCard'
import { useAppSelector, useAppDispatch } from '@/store'
import { 
  selectFilteredStoreBooks, 
  selectUserCredits,
  selectUserPremiumCredits,
  purchaseBook,
  purchasePremiumBook,
  type StoreBook 
} from '@/store/slices/storeSlice'
import { clearCache } from '@/store/slices/audiobooksSlice'
import { Loader2, PackageOpen, CreditCard, AlertTriangle, Crown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import AddToCartModal from '@/components/cart/AddToCartModal'
import CartSidebar from '@/components/cart/CartSidebar'

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
  const userPremiumCredits = useAppSelector(selectUserPremiumCredits)
  
  // Use prop books if provided, otherwise use Redux filtered books
  let books = propBooks ?? reduxBooks
  
  // Apply limit if specified
  if (limit && books.length > limit) {
    books = books.slice(0, limit)
  }

  // Modal state
  const [confirmBook, setConfirmBook] = useState<StoreBook | null>(null)
  const [confirmIsPremium, setConfirmIsPremium] = useState(false)
  const [cartModalBook, setCartModalBook] = useState<StoreBook | null>(null)
  const [showCartSidebar, setShowCartSidebar] = useState(false)
  const [isPurchasing, setIsPurchasing] = useState(false)

  /** Open Add to Cart modal for the chosen book */
  const handleAddToCart = (bookId: string) => {
    const book = books.find((b) => b.id === bookId)
    if (book) setCartModalBook(book)
  }

  /** Open basic-credits confirmation dialog for the chosen book */
  const handleBuyWithCredits = (bookId: string) => {
    const book = books.find((b) => b.id === bookId)
    if (book) { setConfirmBook(book); setConfirmIsPremium(false) }
  }

  /** Open premium-credits confirmation dialog for the chosen book */
  const handleBuyPremium = (bookId: string) => {
    const book = books.find((b) => b.id === bookId)
    if (book) { setConfirmBook(book); setConfirmIsPremium(true) }
  }

  /** Execute the confirmed credits purchase */
  const handleConfirmPurchase = async () => {
    if (!confirmBook) return
    setIsPurchasing(true)
    const book = confirmBook
    try {
      if (confirmIsPremium) {
        await dispatch(purchasePremiumBook({ bookId: book.id, paymentMethod: 'premium_credits' })).unwrap()
      } else {
        await dispatch(purchaseBook({ bookId: book.id, useCredits: true })).unwrap()
      }
      dispatch(clearCache())
      setConfirmBook(null)
      console.log('Toast:', {
        title: 'Purchase successful!',
        description: `"${book.title}" has been added to your library.`,
      })
    } catch (error) {
      console.log('Toast:', {
        title: 'Purchase failed',
        description: error instanceof Error ? error.message : 'Something went wrong. Please try again.',
      })
      // Keep dialog open so user can retry or cancel
    } finally {
      setIsPurchasing(false)
    }
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
              onBuyPremium={handleBuyPremium}
              hasEnoughCredits={userCredits >= book.credits}
              hasEnoughPremiumCredits={userPremiumCredits >= (book.premiumCredits ?? 0)}
            />
          ))}
      </div>

      {/* Loading indicator for infinite scroll (if needed later) */}
      {loading && books.length > 0 && (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* ================================================================ */}
      {/* Credits Purchase Confirmation Dialog                              */}
      {/* ================================================================ */}
      <Dialog open={confirmBook !== null} onOpenChange={(open) => { if (!open) setConfirmBook(null) }}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {confirmIsPremium
                ? <><Crown className="h-5 w-5 text-amber-500" /> Confirm Theatrical Edition Purchase</>
                : <><CreditCard className="h-5 w-5 text-primary" /> Confirm Purchase with Credits</>}
            </DialogTitle>
            <DialogDescription>
              {confirmIsPremium
                ? 'This is a premium edition purchase for a Theatrical audiobook. Theatrical editions require premium credits — basic credits cannot be used.'
                : 'This is a basic credit purchase for a basic edition audiobook. Review your purchase before confirming'}
            </DialogDescription>
          </DialogHeader>

          {confirmBook && (() => {
            const cost   = confirmIsPremium ? (confirmBook.premiumCredits ?? 0) : confirmBook.credits
            const bal    = confirmIsPremium ? userPremiumCredits : userCredits
            const label  = confirmIsPremium ? 'Premium Credit' : 'Credit'
            const icon   = confirmIsPremium
              ? <Crown className="h-3.5 w-3.5 text-amber-500" />
              : <CreditCard className="h-3.5 w-3.5 text-primary" />
            const insufficient = bal < cost
            return (
              <div className="py-4 space-y-4">
                {/* Book preview */}
                <div className="flex gap-4">
                  <div className="w-16 h-20 rounded-md overflow-hidden flex-shrink-0 bg-muted">
                    {confirmBook.coverImage ? (
                      <img src={confirmBook.coverImage} alt={confirmBook.title} className="w-full h-full object-cover" />
                    ) : null}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold leading-tight">{confirmBook.title}</p>
                    <p className="text-sm text-muted-foreground">{confirmBook.author}</p>
                    {confirmIsPremium && (
                      <span className="inline-flex items-center gap-1 mt-1 text-xs font-semibold text-amber-600 dark:text-amber-400">
                        <Crown className="h-3 w-3" /> Theatrical Edition
                      </span>
                    )}
                  </div>
                </div>

                {/* Cost summary */}
                <div className="rounded-lg bg-muted/50 p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Edition</span>
                    <span className="font-medium">{confirmIsPremium ? 'Theatrical (Premium)' : 'Standard'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Purchase price</span>
                    <span className="font-medium flex items-center gap-1">
                      {icon} {cost} {label}{cost !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Your balance</span>
                    <span className={cn('font-medium', insufficient ? 'text-destructive' : 'text-foreground')}>
                      {bal} {label}{bal !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="border-t pt-2 flex justify-between font-medium">
                    <span>Balance after purchase</span>
                    <span className={cn(bal - cost < 0 ? 'text-destructive' : 'text-primary')}>
                      {bal - cost} {label}{(bal - cost) !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>

                {/* Insufficient credits warning */}
                {insufficient && (
                  <div className="flex items-start gap-2 rounded-md bg-destructive/10 p-3 text-destructive text-sm">
                    <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <span>
                      {confirmIsPremium
                        ? `You need ${cost} premium credits but only have ${bal}. Premium credits are required for theatrical editions.`
                        : `You don't have enough credits for this purchase.`}
                    </span>
                  </div>
                )}
              </div>
            )
          })()}

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConfirmBook(null)} disabled={isPurchasing}>
              Cancel
            </Button>
            <Button
              onClick={handleConfirmPurchase}
              disabled={isPurchasing || (confirmBook
                ? (confirmIsPremium ? userPremiumCredits < (confirmBook.premiumCredits ?? 0) : userCredits < confirmBook.credits)
                : false)}
              className={confirmIsPremium ? 'bg-amber-500 hover:bg-amber-600 text-white border-0' : ''}
            >
              {isPurchasing ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Purchasing…</>
              ) : confirmIsPremium ? (
                <><Crown className="h-4 w-4 mr-2" /> Confirm Theatrical Purchase</>
              ) : (
                <><CreditCard className="h-4 w-4 mr-2" /> Confirm Purchase</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add to Cart Modal */}
      <AddToCartModal
        book={cartModalBook}
        isOpen={cartModalBook !== null}
        onClose={() => setCartModalBook(null)}
        onOpenCart={() => { setCartModalBook(null); setShowCartSidebar(true) }}
      />

      {/* Cart Sidebar */}
      <CartSidebar
        isOpen={showCartSidebar}
        onClose={() => setShowCartSidebar(false)}
      />
    </section>
  )
}
