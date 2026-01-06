/**
 * Store Book Detail Page
 * 
 * A comprehensive page for viewing and purchasing audiobooks from the store.
 * Displays full book information, synopsis, chapter breakdown, and purchase options.
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - Full-size book cover with metadata
 * - Prominent buy button with price/credits
 * - Listen to sample functionality
 * - Synopsis section
 * - Chapter breakdown
 * - Related books recommendations
 * - Star ratings and reviews summary
 * 
 * REDUX INTEGRATION:
 * - Uses storeSlice for book data
 * - Uses audioPlayerSlice for sample playback
 * - Uses userSlice for credits balance
 * 
 * API INTEGRATION POINTS:
 * - fetchStoreBookDetails: Get full book details by ID
 * - purchaseBook: Process purchase with credits or payment
 * - playSample: Stream audio sample
 * - getRelatedBooks: Fetch recommendations
 */

import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { 
  ArrowLeft, 
  Play, 
  Pause,
  ShoppingCart, 
  CreditCard, 
  Clock, 
  Calendar, 
  Mic2, 
  BookOpen,
  Star,
  Globe,
  Building2,
  Tag,
  Share2,
  Heart,
  ChevronDown,
  ChevronUp,
  Volume2,
  CheckCircle2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { AddToCartModal } from '@/components/cart/AddToCartModal'
import { CartSidebar } from '@/components/cart/CartSidebar'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { 
  fetchStoreBookDetails,
  purchaseBook,
  selectStoreBookById,
  selectUserCredits,
  selectStoreBooksLoading,
} from '@/store/slices/storeSlice'
import type { StoreBook } from '@/store/slices/storeSlice'

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
    return `${hours} hr ${minutes} min`
  }
  return `${minutes} min`
}

/**
 * Format price from cents to dollars
 */
function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

/**
 * Format date to readable string
 */
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/**
 * Star Rating Display Component
 */
function StarRating({ 
  rating, 
  reviewCount,
  size = 'default' 
}: { 
  rating: number
  reviewCount: number
  size?: 'default' | 'large'
}) {
  const fullStars = Math.floor(rating)
  const hasHalfStar = rating - fullStars >= 0.5
  const starSize = size === 'large' ? 'h-5 w-5' : 'h-4 w-4'
  
  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center">
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={cn(
              starSize,
              i < fullStars
                ? "fill-yellow-400 text-yellow-400"
                : i === fullStars && hasHalfStar
                ? "fill-yellow-400/50 text-yellow-400"
                : "fill-muted text-muted"
            )}
          />
        ))}
      </div>
      <span className={cn(
        "font-medium",
        size === 'large' ? "text-lg" : "text-sm"
      )}>
        {rating.toFixed(1)}
      </span>
      <span className="text-muted-foreground text-sm">
        ({reviewCount.toLocaleString()} ratings)
      </span>
    </div>
  )
}

/**
 * Sample Audio Player Component
 * 
 * TODO: API INTEGRATION
 * Replace the sample audio URL handling with actual streaming:
 * - Use authenticated streaming endpoint
 * - Handle streaming errors
 * - Track sample plays for analytics
 */
function SamplePlayer({ 
  sampleUrl, 
  bookTitle 
}: { 
  sampleUrl?: string
  bookTitle: string 
}) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(0)
  const audioRef = useRef<HTMLAudioElement>(null)

  // Handle play/pause toggle
  const togglePlay = () => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  // Update progress as audio plays
  const handleTimeUpdate = () => {
    if (!audioRef.current) return
    const current = audioRef.current.currentTime
    const total = audioRef.current.duration
    setProgress((current / total) * 100)
  }

  // Handle audio loaded
  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration)
    }
  }

  // Handle audio ended
  const handleEnded = () => {
    setIsPlaying(false)
    setProgress(0)
  }

  // Demo sample URL fallback
  const audioUrl = sampleUrl || 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'

  return (
    <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        preload="metadata"
      />

      {/* Play/Pause Button */}
      <Button
        variant="outline"
        size="icon"
        className="h-10 w-10 rounded-full flex-shrink-0"
        onClick={togglePlay}
      >
        {isPlaying ? (
          <Pause className="h-4 w-4" />
        ) : (
          <Play className="h-4 w-4 ml-0.5" fill="currentColor" />
        )}
      </Button>

      {/* Progress Bar and Label */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium truncate">
            Sample: {bookTitle}
          </span>
          <span className="text-xs text-muted-foreground ml-2 flex-shrink-0">
            {duration > 0 ? formatDuration(duration) : '--:--'}
          </span>
        </div>
        <Progress value={progress} className="h-1.5" />
      </div>

      {/* Volume Icon */}
      <Volume2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
    </div>
  )
}

/**
 * Purchase Button Section
 * 
 * TODO: API INTEGRATION
 * - Connect to payment processor for credit card purchases
 * - Connect to credits system for credit-based purchases
 * - Handle purchase confirmation/success states
 * - Redirect to library after successful purchase
 */
function PurchaseSection({ 
  book, 
  userCredits,
  onPurchaseWithCredits,
  onPurchaseWithCard,
  onAddToCart,
  isPurchasing,
}: { 
  book: StoreBook
  userCredits: number
  onPurchaseWithCredits: () => void
  onPurchaseWithCard: () => void
  onAddToCart: () => void
  isPurchasing: boolean
}) {
  const hasEnoughCredits = userCredits >= book.credits
  const discount = book.originalPrice 
    ? Math.round((1 - book.price / book.originalPrice) * 100) 
    : 0

  return (
    <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
      <CardContent className="p-6 space-y-4">
        {/* Price Display */}
        <div className="text-center">
          {book.isOnSale && book.originalPrice && (
            <div className="flex items-center justify-center gap-2 mb-1">
              <span className="text-lg text-muted-foreground line-through">
                {formatPrice(book.originalPrice)}
              </span>
              <Badge variant="destructive" size="sm">
                {discount}% OFF
              </Badge>
            </div>
          )}
          <div className="text-4xl font-bold text-primary">
            {formatPrice(book.price)}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            or {book.credits} credit{book.credits > 1 ? 's' : ''}
          </p>
        </div>

        <Separator />

        {/* Purchase Buttons */}
        <div className="space-y-3">
          {/* Add to Cart - Primary CTA */}
          <Button
            size="lg"
            className="w-full h-14 text-lg font-semibold"
            onClick={onAddToCart}
            disabled={isPurchasing}
          >
            <ShoppingCart className="h-5 w-5 mr-2" />
            Add to Cart
          </Button>

          {/* Buy with Credits */}
          <Button
            variant="outline"
            size="lg"
            className="w-full h-12"
            onClick={onPurchaseWithCredits}
            disabled={!hasEnoughCredits || isPurchasing}
          >
            {isPurchasing ? (
              <>Processing...</>
            ) : (
              <>
                <CreditCard className="h-4 w-4 mr-2" />
                Buy Now with {book.credits} Credit{book.credits > 1 ? 's' : ''}
              </>
            )}
          </Button>

          {!hasEnoughCredits && (
            <p className="text-xs text-center text-destructive">
              You have {userCredits} credit{userCredits !== 1 ? 's' : ''}. 
              <Link to="/credits" className="underline ml-1">Get more credits</Link>
            </p>
          )}

          {/* Buy with Card */}
          <Button
            variant="ghost"
            size="sm"
            className="w-full"
            onClick={onPurchaseWithCard}
            disabled={isPurchasing}
          >
            Or pay {formatPrice(book.price)} with card
          </Button>
        </div>

        {/* Assurance Text */}
        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground pt-2">
          <CheckCircle2 className="h-3 w-3" />
          <span>Instant access after purchase</span>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Metadata Item Component
 */
function MetaItem({ 
  icon: Icon, 
  label, 
  value 
}: { 
  icon: React.ElementType
  label: string
  value: string | number 
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="font-medium">{value}</p>
      </div>
    </div>
  )
}

/**
 * Chapter List Item
 */
function ChapterItem({ 
  index, 
  title, 
  duration 
}: { 
  index: number
  title: string
  duration?: number 
}) {
  return (
    <div className="flex items-center gap-4 py-3 border-b border-border/50 last:border-0">
      <span className="text-sm font-medium text-muted-foreground w-8 flex-shrink-0">
        {index.toString().padStart(2, '0')}
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{title}</p>
      </div>
      {duration && (
        <span className="text-sm text-muted-foreground flex-shrink-0">
          {formatDuration(duration)}
        </span>
      )}
    </div>
  )
}

/**
 * Expandable Synopsis Section
 */
function Synopsis({ description }: { description: string }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const isLong = description.length > 400

  return (
    <div className="space-y-3">
      <h2 className="text-xl font-semibold">Synopsis</h2>
      <div className="relative">
        <p className={cn(
          "text-muted-foreground leading-relaxed",
          !isExpanded && isLong && "line-clamp-4"
        )}>
          {description}
        </p>
        {isLong && !isExpanded && (
          <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-background to-transparent" />
        )}
      </div>
      {isLong && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-primary"
        >
          {isExpanded ? (
            <>Show Less <ChevronUp className="h-4 w-4 ml-1" /></>
          ) : (
            <>Read More <ChevronDown className="h-4 w-4 ml-1" /></>
          )}
        </Button>
      )}
    </div>
  )
}

// ============================================================================
// MOCK CHAPTERS (for demo purposes)
// ============================================================================

const mockChapters = [
  { id: 'ch1', title: 'Introduction - The Surprising Power of Atomic Habits', duration: 1800 },
  { id: 'ch2', title: 'Chapter 1: The Fundamentals', duration: 2400 },
  { id: 'ch3', title: 'Chapter 2: How Your Habits Shape Your Identity', duration: 2100 },
  { id: 'ch4', title: 'Chapter 3: How to Build Better Habits in 4 Simple Steps', duration: 2700 },
  { id: 'ch5', title: 'Chapter 4: The Man Who Didn\'t Look Right', duration: 1950 },
  { id: 'ch6', title: 'Chapter 5: The Best Way to Start a New Habit', duration: 2250 },
  { id: 'ch7', title: 'Chapter 6: Motivation Is Overrated', duration: 2400 },
  { id: 'ch8', title: 'Chapter 7: The Secret to Self-Control', duration: 1800 },
  { id: 'ch9', title: 'Chapter 8: How to Make a Habit Irresistible', duration: 2100 },
  { id: 'ch10', title: 'Conclusion - The Secret to Results That Last', duration: 1500 },
]

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function StoreBookDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  
  // Redux state
  const book = useAppSelector((state) => selectStoreBookById(state, id || ''))
  const userCredits = useAppSelector(selectUserCredits)
  const loading = useAppSelector(selectStoreBooksLoading)
  
  // Local state
  const [isPurchasing, setIsPurchasing] = useState(false)
  const [showAllChapters, setShowAllChapters] = useState(false)
  const [showAddToCartModal, setShowAddToCartModal] = useState(false)
  const [showCartSidebar, setShowCartSidebar] = useState(false)

  /**
   * Fetch book details on mount
   * 
   * TODO: API INTEGRATION
   * This dispatches fetchStoreBookDetails which currently uses mock data.
   * Replace with actual API call in the thunk.
   */
  useEffect(() => {
    if (id) {
      dispatch(fetchStoreBookDetails(id))
    }
  }, [id, dispatch])

  /**
   * Handle purchase with credits
   * 
   * TODO: API INTEGRATION
   * - Call purchase API endpoint
   * - Deduct credits from user account
   * - Add book to user's library
   * - Show success notification
   * - Redirect to library or book player
   */
  const handlePurchaseWithCredits = async () => {
    if (!book) return
    
    setIsPurchasing(true)
    try {
      await dispatch(purchaseBook({ bookId: book.id, useCredits: true })).unwrap()
      // TODO: Show success toast
      // TODO: Navigate to library or start playing
      navigate('/library')
    } catch (error) {
      // TODO: Show error toast
      console.error('Purchase failed:', error)
    } finally {
      setIsPurchasing(false)
    }
  }

  /**
   * Handle purchase with credit card
   * 
   * TODO: API INTEGRATION
   * - Open payment modal/redirect to payment page
   * - Process payment via Stripe/payment processor
   * - Add book to user's library on success
   * - Handle payment failures gracefully
   */
  const handlePurchaseWithCard = async () => {
    if (!book) return
    
    setIsPurchasing(true)
    try {
      // TODO: Open payment modal or redirect to checkout
      await dispatch(purchaseBook({ bookId: book.id, useCredits: false })).unwrap()
      navigate('/library')
    } catch (error) {
      console.error('Purchase failed:', error)
    } finally {
      setIsPurchasing(false)
    }
  }

  // Loading state
  if (loading && !book) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse space-y-8">
          <div className="h-8 w-32 bg-muted rounded" />
          <div className="grid lg:grid-cols-[350px_1fr_300px] gap-8">
            <div className="aspect-[3/4] bg-muted rounded-xl" />
            <div className="space-y-4">
              <div className="h-10 bg-muted rounded w-3/4" />
              <div className="h-6 bg-muted rounded w-1/2" />
              <div className="h-4 bg-muted rounded w-full" />
              <div className="h-4 bg-muted rounded w-full" />
            </div>
            <div className="h-64 bg-muted rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  // Not found state
  if (!book) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
        <h1 className="text-2xl font-bold mb-2">Book Not Found</h1>
        <p className="text-muted-foreground mb-6">
          The audiobook you're looking for doesn't exist or has been removed.
        </p>
        <Button onClick={() => navigate('/store')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Store
        </Button>
      </div>
    )
  }

  // Prepare chapter data (use mock for demo)
  const chapters = mockChapters
  const visibleChapters = showAllChapters ? chapters : chapters.slice(0, 5)

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back Button */}
      <Button 
        variant="ghost" 
        onClick={() => navigate('/store')}
        className="mb-6 -ml-2"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Store
      </Button>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-[350px_1fr_320px] gap-8">
        {/* ============================================================== */}
        {/* LEFT COLUMN - Book Cover & Sample */}
        {/* ============================================================== */}
        <div className="space-y-6">
          {/* Book Cover */}
          <div className="relative">
            <div className="aspect-[3/4] rounded-xl overflow-hidden shadow-2xl bg-gradient-to-br from-primary/20 to-primary/40">
              {book.coverImage ? (
                <img
                  src={book.coverImage}
                  alt={`${book.title} by ${book.author}`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <BookOpen className="w-24 h-24 text-primary/60" />
                </div>
              )}
            </div>
            
            {/* Sale Badge */}
            {book.isOnSale && (
              <Badge 
                variant="destructive" 
                className="absolute top-4 right-4 text-sm px-3 py-1"
              >
                SALE
              </Badge>
            )}
          </div>

          {/* Sample Player */}
          <div className="space-y-2">
            <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
              Listen to a Sample
            </h3>
            <SamplePlayer 
              sampleUrl={book.sampleAudioUrl} 
              bookTitle={book.title} 
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="flex-1">
              <Heart className="h-4 w-4 mr-2" />
              Wishlist
            </Button>
            <Button variant="outline" size="sm" className="flex-1">
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </Button>
          </div>
        </div>

        {/* ============================================================== */}
        {/* CENTER COLUMN - Book Details */}
        {/* ============================================================== */}
        <div className="space-y-8">
          {/* Genre Badge */}
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary" className="text-sm">
              {book.genre}
            </Badge>
            {book.series && (
              <Badge variant="outline" className="text-sm">
                {book.series} #{book.seriesNumber}
              </Badge>
            )}
          </div>

          {/* Title & Author */}
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold mb-2">{book.title}</h1>
            <p className="text-xl text-muted-foreground">
              by <span className="text-foreground font-medium">{book.author}</span>
            </p>
          </div>

          {/* Rating */}
          <StarRating 
            rating={book.rating} 
            reviewCount={book.reviewCount}
            size="large"
          />

          {/* Key Metadata */}
          <div className="grid grid-cols-2 gap-4">
            <MetaItem 
              icon={Clock} 
              label="Length" 
              value={formatDuration(book.duration)} 
            />
            <MetaItem 
              icon={Mic2} 
              label="Narrator" 
              value={book.narrator} 
            />
            <MetaItem 
              icon={Calendar} 
              label="Release Date" 
              value={formatDate(book.releaseDate)} 
            />
            <MetaItem 
              icon={Globe} 
              label="Language" 
              value={book.language} 
            />
            <MetaItem 
              icon={Building2} 
              label="Publisher" 
              value={book.publisher} 
            />
            <MetaItem 
              icon={Calendar} 
              label="Published Year" 
              value={book.publishedYear.toString()} 
            />
          </div>

          <Separator />

          {/* Synopsis */}
          <Synopsis description={book.description} />

          <Separator />

          {/* Chapters */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">
                Chapters
                <span className="text-muted-foreground font-normal text-base ml-2">
                  ({chapters.length} chapters)
                </span>
              </h2>
            </div>
            
            <div>
              {visibleChapters.map((chapter, index) => (
                <ChapterItem
                  key={chapter.id}
                  index={index + 1}
                  title={chapter.title}
                  duration={chapter.duration}
                />
              ))}
            </div>

            {chapters.length > 5 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAllChapters(!showAllChapters)}
                className="w-full"
              >
                {showAllChapters ? (
                  <>Show Less <ChevronUp className="h-4 w-4 ml-1" /></>
                ) : (
                  <>Show All {chapters.length} Chapters <ChevronDown className="h-4 w-4 ml-1" /></>
                )}
              </Button>
            )}
          </div>

          {/* Tags */}
          {book.tags && book.tags.length > 0 && (
            <>
              <Separator />
              <div className="space-y-3">
                <h3 className="font-medium flex items-center gap-2">
                  <Tag className="h-4 w-4" />
                  Tags
                </h3>
                <div className="flex flex-wrap gap-2">
                  {book.tags.map((tag) => (
                    <Badge 
                      key={tag} 
                      variant="outline" 
                      className="cursor-pointer hover:bg-accent"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* ============================================================== */}
        {/* RIGHT COLUMN - Purchase Section (Sticky) */}
        {/* ============================================================== */}
        <div className="lg:sticky lg:top-8 h-fit space-y-6">
          {/* Purchase Card */}
          <PurchaseSection
            book={book}
            userCredits={userCredits}
            onPurchaseWithCredits={handlePurchaseWithCredits}
            onPurchaseWithCard={handlePurchaseWithCard}
            onAddToCart={() => setShowAddToCartModal(true)}
            isPurchasing={isPurchasing}
          />

          {/* User Credits Info */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" />
                  <span className="font-medium">Your Credits</span>
                </div>
                <span className="text-2xl font-bold">{userCredits}</span>
              </div>
              <Button 
                variant="link" 
                size="sm" 
                className="w-full mt-2 text-primary"
                asChild
              >
                <Link to="/credits">Get More Credits</Link>
              </Button>
            </CardContent>
          </Card>

          {/* Guarantee Note */}
          <div className="text-center text-xs text-muted-foreground space-y-1">
            <p>✓ Yours to keep forever</p>
            <p>✓ Listen on any device</p>
            <p>✓ 30-day satisfaction guarantee</p>
          </div>
        </div>
      </div>
      
      {/* Add to Cart Modal */}
      <AddToCartModal
        book={book}
        isOpen={showAddToCartModal}
        onClose={() => setShowAddToCartModal(false)}
        onOpenCart={() => setShowCartSidebar(true)}
      />
      
      {/* Cart Sidebar */}
      <CartSidebar
        isOpen={showCartSidebar}
        onClose={() => setShowCartSidebar(false)}
      />
    </div>
  )
}
