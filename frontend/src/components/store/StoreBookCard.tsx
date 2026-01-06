/**
 * StoreBookCard Component
 * 
 * Displays a single audiobook available for purchase in the store.
 * Features an interactive hover overlay showing detailed information
 * including description, narrator, duration, and pricing.
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - Book cover image with fallback
 * - Genre badge
 * - Sale indicator
 * - Hover overlay with full details
 * - Pricing display (credits and price)
 * - Star rating display
 * - Responsive design
 * 
 * API INTEGRATION:
 * - Purchase button onClick should dispatch purchaseBook action
 * - Sample audio playback can be triggered from here
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Clock, 
  User, 
  Mic2, 
  Star, 
  ShoppingCart,
  CreditCard,
  Play,
  BookOpen
} from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { StoreBook } from '@/store/slices/storeSlice'

// ============================================================================
// TYPES
// ============================================================================

interface StoreBookCardProps {
  /** The store book data to display */
  book: StoreBook
  /** Optional callback when user clicks "Add to Cart" */
  onAddToCart?: (bookId: string) => void
  /** Optional callback when user clicks "Buy with Credits" */
  onBuyWithCredits?: (bookId: string) => void
  /** Whether the user has enough credits to purchase */
  hasEnoughCredits?: boolean
  /** Optional additional class names */
  className?: string
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Format duration from seconds to human-readable string
 */
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m`
}

/**
 * Format price from cents to dollars
 */
function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

/**
 * Render star rating display
 */
function StarRating({ rating, reviewCount }: { rating: number; reviewCount: number }) {
  const fullStars = Math.floor(rating)
  const hasHalfStar = rating - fullStars >= 0.5
  
  return (
    <div className="flex items-center gap-1">
      <div className="flex items-center">
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={cn(
              "h-3.5 w-3.5",
              i < fullStars
                ? "fill-yellow-400 text-yellow-400"
                : i === fullStars && hasHalfStar
                ? "fill-yellow-400/50 text-yellow-400"
                : "fill-muted text-muted"
            )}
          />
        ))}
      </div>
      <span className="text-xs text-muted-foreground">
        {rating.toFixed(1)} ({reviewCount.toLocaleString()})
      </span>
    </div>
  )
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function StoreBookCard({
  book,
  onAddToCart,
  onBuyWithCredits,
  hasEnoughCredits = true,
  className,
}: StoreBookCardProps) {
  // Track hover state for showing detailed overlay
  const [isHovered, setIsHovered] = useState(false)

  // Destructure book properties
  const {
    id,
    title,
    author,
    description,
    coverImage,
    duration,
    narrator,
    genre,
    rating,
    reviewCount,
    price,
    credits,
    originalPrice,
    isOnSale,
    series,
    seriesNumber,
  } = book

  /**
   * Handle add to cart click
   * 
   * TODO: API INTEGRATION
   * Connect this to your cart/purchase system:
   * dispatch(addToCart(id))
   */
  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onAddToCart?.(id)
  }

  /**
   * Handle buy with credits click
   * 
   * TODO: API INTEGRATION
   * Connect this to your credits purchase system:
   * dispatch(purchaseBook({ bookId: id, useCredits: true }))
   */
  const handleBuyWithCredits = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onBuyWithCredits?.(id)
  }

  return (
    <Link to={`/store/book/${id}`} className="block h-full">
      <Card
        className={cn(
          "relative overflow-hidden transition-all duration-300 h-full flex flex-col",
          "hover:shadow-xl hover:scale-[1.02]",
          "cursor-pointer group",
          className
        )}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Book Cover Image */}
        <div className="aspect-[3/4] relative overflow-hidden bg-gradient-to-br from-primary/20 to-primary/40 flex-shrink-0">
          {coverImage ? (
            <img
              src={coverImage}
              alt={`${title} by ${author}`}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
              loading="lazy"
            />
          ) : (
            // Fallback when no cover image
            <div className="w-full h-full flex items-center justify-center">
              <BookOpen className="w-20 h-20 text-primary/60" />
            </div>
          )}

          {/* Genre Badge - Top Left */}
          {genre && (
            <div className="absolute top-2 left-2 z-10">
              <Badge variant="secondary" className="backdrop-blur-sm bg-background/80">
                {genre}
              </Badge>
            </div>
          )}

          {/* Sale Badge - Top Right */}
          {isOnSale && (
            <div className="absolute top-2 right-2 z-10">
              <Badge variant="destructive">
                SALE
              </Badge>
            </div>
          )}

          {/* Hover Overlay - Full Details */}
          <div
            className={cn(
              "absolute inset-0 bg-gradient-to-t from-black/95 via-black/80 to-black/40",
              "flex flex-col justify-end p-4",
              "transition-all duration-300",
              isHovered ? "opacity-100" : "opacity-0"
            )}
          >
            {/* Description */}
            <p className="text-white/90 text-sm line-clamp-4 mb-3">
              {description}
            </p>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs text-white/80 mb-3">
              {/* Duration */}
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{formatDuration(duration)}</span>
              </div>

              {/* Narrator */}
              <div className="flex items-center gap-1">
                <Mic2 className="h-3 w-3" />
                <span className="truncate">{narrator}</span>
              </div>

              {/* Series Info (if applicable) */}
              {series && (
                <div className="col-span-2 flex items-center gap-1">
                  <BookOpen className="h-3 w-3" />
                  <span className="truncate">
                    {series} #{seriesNumber}
                  </span>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              {/* Buy with Credits Button */}
              <Button
                size="sm"
                variant="secondary"
                className="flex-1 h-8 text-xs"
                onClick={handleBuyWithCredits}
                disabled={!hasEnoughCredits}
              >
                <CreditCard className="h-3 w-3 mr-1" />
                {credits} Credit{credits > 1 ? 's' : ''}
              </Button>

              {/* Add to Cart Button */}
              <Button
                size="sm"
                className="flex-1 h-8 text-xs"
                onClick={handleAddToCart}
              >
                <ShoppingCart className="h-3 w-3 mr-1" />
                {formatPrice(price)}
              </Button>
            </div>

            {/* Sample Audio Button */}
            <Button
              size="sm"
              variant="ghost"
              className="mt-2 h-7 text-xs text-white/80 hover:text-white hover:bg-white/10"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                // TODO: Play sample audio
                // dispatch(playSample(book.sampleAudioUrl))
              }}
            >
              <Play className="h-3 w-3 mr-1" />
              Play Sample
            </Button>
          </div>
        </div>

        {/* Card Footer - Always Visible */}
        <div className="p-3 space-y-2 h-[140px] flex flex-col">
          {/* Title */}
          <h3 className="font-semibold text-sm leading-tight line-clamp-2 group-hover:text-primary transition-colors min-h-[2.5rem]">
            {title}
          </h3>

          {/* Author */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <User className="h-3 w-3 flex-shrink-0" />
            <span className="truncate">{author}</span>
          </div>

          {/* Rating */}
          <StarRating rating={rating} reviewCount={reviewCount} />

          {/* Pricing Row - Push to bottom */}
          <div className="flex items-center justify-between pt-1 border-t border-border/50 mt-auto">
            {/* Credit Price */}
            <div className="flex items-center gap-1 text-xs">
              <CreditCard className="h-3 w-3 text-primary flex-shrink-0" />
              <span className="font-medium">{credits} Credit{credits > 1 ? 's' : ''}</span>
            </div>

            {/* Dollar Price */}
            <div className="text-right">
              {isOnSale && originalPrice && (
                <span className="text-xs text-muted-foreground line-through mr-1">
                  {formatPrice(originalPrice)}
                </span>
              )}
              <span className={cn(
                "text-sm font-bold",
                isOnSale ? "text-destructive" : "text-foreground"
              )}>
                {formatPrice(price)}
              </span>
            </div>
          </div>
        </div>
      </Card>
    </Link>
  )
}
