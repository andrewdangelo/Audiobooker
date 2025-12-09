/**
 * Store Page
 * 
 * The main audiobook marketplace/store page where users can browse,
 * search, filter, and purchase audiobooks.
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - Header with user credits display
 * - Search bar with real-time filtering
 * - Genre filter dropdown
 * - Sort options
 * - Featured books section
 * - New releases section
 * - Best sellers section
 * - Main book grid with all books
 * - Responsive design
 * 
 * STATE MANAGEMENT:
 * - Uses Redux for all store state (books, filters, search)
 * - Dispatches fetchStoreBooks on mount to load catalog
 * - Supports caching to reduce API calls
 * 
 * API INTEGRATION POINTS:
 * - fetchStoreBooks thunk: Replace mock data with API call
 * - Search can be server-side or client-side (currently client-side)
 * - Filters can be passed to API for server-side filtering
 */

import { useEffect, useState } from 'react'
import { 
  Search, 
  SlidersHorizontal, 
  CreditCard,
  ChevronDown,
  X,
  Sparkles,
  Clock,
  TrendingUp,
  Filter,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import StoreBookGrid from '@/components/store/StoreBookGrid'
import { 
  useAppDispatch, 
  useAppSelector,
  fetchStoreBooks,
  setStoreSearchQuery,
  updateStoreFilter,
  clearStoreFilters,
  setStoreSort,
  selectStoreBooksLoading,
  selectStoreBooksError,
  selectStoreSearchQuery,
  selectStoreFilters,
  selectStoreSort,
  selectUserCredits,
  selectAvailableGenres,
  selectFeaturedBooks,
  selectNewReleases,
  selectBestSellers,
  selectFilteredStoreBooks,
  type StoreSortOption,
} from '@/store'
import { cn } from '@/lib/utils'

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Sort options for the store
 */
const SORT_OPTIONS: { value: StoreSortOption; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'bestselling', label: 'Best Selling' },
  { value: 'newest', label: 'Newest' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'price-low', label: 'Price: Low to High' },
  { value: 'price-high', label: 'Price: High to Low' },
  { value: 'title', label: 'Title A-Z' },
  { value: 'author', label: 'Author A-Z' },
]

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/**
 * User credits display banner
 */
function CreditsBanner({ credits }: { credits: number }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-lg border border-primary/20">
      <CreditCard className="h-5 w-5 text-primary" />
      <span className="font-medium">
        {credits} Credit{credits !== 1 ? 's' : ''} Available
      </span>
      <Button variant="link" size="sm" className="text-primary h-auto p-0 ml-2">
        Get More
      </Button>
    </div>
  )
}

/**
 * Genre filter dropdown
 */
function GenreFilter({ 
  genres, 
  selectedGenre, 
  onSelect 
}: { 
  genres: string[]
  selectedGenre?: string
  onSelect: (genre: string | undefined) => void 
}) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <Button
        variant="outline"
        className="min-w-[140px] justify-between"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="truncate">
          {selectedGenre || 'All Genres'}
        </span>
        <ChevronDown className={cn(
          "h-4 w-4 ml-2 transition-transform",
          isOpen && "rotate-180"
        )} />
      </Button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)} 
          />
          {/* Menu */}
          <div className="absolute z-50 mt-2 w-56 rounded-md border bg-popover p-1 shadow-lg">
            <button
              className={cn(
                "w-full px-3 py-2 text-left text-sm rounded-sm hover:bg-accent",
                !selectedGenre && "bg-accent"
              )}
              onClick={() => {
                onSelect(undefined)
                setIsOpen(false)
              }}
            >
              All Genres
            </button>
            {genres.map((genre) => (
              <button
                key={genre}
                className={cn(
                  "w-full px-3 py-2 text-left text-sm rounded-sm hover:bg-accent",
                  selectedGenre === genre && "bg-accent"
                )}
                onClick={() => {
                  onSelect(genre)
                  setIsOpen(false)
                }}
              >
                {genre}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Sort dropdown
 */
function SortDropdown({ 
  currentSort, 
  onSelect 
}: { 
  currentSort: StoreSortOption
  onSelect: (sort: StoreSortOption) => void 
}) {
  const [isOpen, setIsOpen] = useState(false)
  const currentLabel = SORT_OPTIONS.find(o => o.value === currentSort)?.label || 'Sort'

  return (
    <div className="relative">
      <Button
        variant="outline"
        className="min-w-[160px] justify-between"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="truncate">{currentLabel}</span>
        <ChevronDown className={cn(
          "h-4 w-4 ml-2 transition-transform",
          isOpen && "rotate-180"
        )} />
      </Button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)} 
          />
          <div className="absolute right-0 z-50 mt-2 w-48 rounded-md border bg-popover p-1 shadow-lg">
            {SORT_OPTIONS.map((option) => (
              <button
                key={option.value}
                className={cn(
                  "w-full px-3 py-2 text-left text-sm rounded-sm hover:bg-accent",
                  currentSort === option.value && "bg-accent"
                )}
                onClick={() => {
                  onSelect(option.value)
                  setIsOpen(false)
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Active filters display with clear option
 */
function ActiveFilters({ 
  filters, 
  searchQuery, 
  onClearFilter, 
  onClearAll 
}: { 
  filters: { genre?: string }
  searchQuery: string
  onClearFilter: (key: string) => void
  onClearAll: () => void
}) {
  const hasFilters = filters.genre || searchQuery

  if (!hasFilters) return null

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-sm text-muted-foreground">Active filters:</span>
      
      {searchQuery && (
        <Badge variant="secondary" className="gap-1">
          Search: "{searchQuery}"
          <button onClick={() => onClearFilter('search')}>
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}
      
      {filters.genre && (
        <Badge variant="secondary" className="gap-1">
          {filters.genre}
          <button onClick={() => onClearFilter('genre')}>
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}

      <Button 
        variant="ghost" 
        size="sm" 
        className="h-6 px-2 text-xs"
        onClick={onClearAll}
      >
        Clear All
      </Button>
    </div>
  )
}

/**
 * Section header with icon
 */
function SectionHeader({ 
  icon: Icon, 
  title, 
  subtitle 
}: { 
  icon: React.ElementType
  title: string
  subtitle?: string
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="p-2 rounded-lg bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div>
        <h2 className="text-xl font-bold">{title}</h2>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function Store() {
  const dispatch = useAppDispatch()
  
  // Redux state selectors
  const loading = useAppSelector(selectStoreBooksLoading)
  const error = useAppSelector(selectStoreBooksError)
  const searchQuery = useAppSelector(selectStoreSearchQuery)
  const filters = useAppSelector(selectStoreFilters)
  const { sortBy } = useAppSelector(selectStoreSort)
  const userCredits = useAppSelector(selectUserCredits)
  const availableGenres = useAppSelector(selectAvailableGenres)
  const featuredBooks = useAppSelector(selectFeaturedBooks)
  const newReleases = useAppSelector(selectNewReleases)
  const bestSellers = useAppSelector(selectBestSellers)
  const allFilteredBooks = useAppSelector(selectFilteredStoreBooks)

  // Track if we're showing filtered results (hide featured sections)
  const isFiltering = searchQuery || filters.genre

  /**
   * Fetch store books on component mount
   * 
   * TODO: API INTEGRATION
   * This dispatches the fetchStoreBooks thunk which currently uses mock data.
   * The thunk includes caching logic - it won't refetch if cache is valid.
   */
  useEffect(() => {
    dispatch(fetchStoreBooks())
  }, [dispatch])

  /**
   * Handle search input change
   */
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setStoreSearchQuery(e.target.value))
  }

  /**
   * Handle genre filter selection
   */
  const handleGenreSelect = (genre: string | undefined) => {
    dispatch(updateStoreFilter({ key: 'genre', value: genre }))
  }

  /**
   * Handle sort selection
   */
  const handleSortSelect = (sort: StoreSortOption) => {
    dispatch(setStoreSort({ sortBy: sort }))
  }

  /**
   * Clear a specific filter
   */
  const handleClearFilter = (key: string) => {
    if (key === 'search') {
      dispatch(setStoreSearchQuery(''))
    } else if (key === 'genre') {
      dispatch(updateStoreFilter({ key: 'genre', value: undefined }))
    }
  }

  /**
   * Clear all filters and search
   */
  const handleClearAll = () => {
    dispatch(clearStoreFilters())
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* ================================================================== */}
      {/* PAGE HEADER */}
      {/* ================================================================== */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audiobook Store</h1>
          <p className="text-muted-foreground mt-1">
            Discover your next favorite listen
          </p>
        </div>
        
        {/* User Credits Banner */}
        <CreditsBanner credits={userCredits} />
      </div>

      {/* ================================================================== */}
      {/* SEARCH AND FILTERS BAR */}
      {/* ================================================================== */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search by title, author, or narrator..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="pl-10"
          />
        </div>

        {/* Filter Controls */}
        <div className="flex gap-2 flex-wrap">
          {/* Genre Filter */}
          <GenreFilter
            genres={availableGenres}
            selectedGenre={filters.genre}
            onSelect={handleGenreSelect}
          />

          {/* Sort Dropdown */}
          <SortDropdown
            currentSort={sortBy}
            onSelect={handleSortSelect}
          />

          {/* More Filters Button (for future expansion) */}
          <Button variant="outline" size="icon" className="hidden sm:flex">
            <SlidersHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Active Filters Display */}
      <ActiveFilters
        filters={filters}
        searchQuery={searchQuery}
        onClearFilter={handleClearFilter}
        onClearAll={handleClearAll}
      />

      {/* ================================================================== */}
      {/* ERROR STATE */}
      {/* ================================================================== */}
      {error && (
        <div className="text-center py-8 px-4 rounded-lg bg-destructive/10 border border-destructive/20">
          <p className="text-destructive font-medium">{error}</p>
          <Button 
            variant="outline" 
            className="mt-4"
            onClick={() => dispatch(fetchStoreBooks())}
          >
            Try Again
          </Button>
        </div>
      )}

      {/* ================================================================== */}
      {/* LOADING STATE (Initial Load) */}
      {/* ================================================================== */}
      {loading && allFilteredBooks.length === 0 && (
        <div className="space-y-8">
          <StoreBookGrid loading={true} limit={4} columns={4} />
          <StoreBookGrid loading={true} limit={8} />
        </div>
      )}

      {/* ================================================================== */}
      {/* MAIN CONTENT */}
      {/* ================================================================== */}
      {!loading && !error && (
        <>
          {/* When filtering, show flat results */}
          {isFiltering ? (
            <StoreBookGrid
              title={`Search Results (${allFilteredBooks.length})`}
              subtitle={searchQuery ? `Showing results for "${searchQuery}"` : undefined}
            />
          ) : (
            /* When not filtering, show categorized sections */
            <div className="space-y-12">
              {/* Featured Books Section */}
              {featuredBooks.length > 0 && (
                <section className="space-y-4">
                  <SectionHeader
                    icon={Sparkles}
                    title="Featured"
                    subtitle="Hand-picked recommendations for you"
                  />
                  <StoreBookGrid
                    books={featuredBooks}
                    columns={4}
                    showEmptyState={false}
                  />
                </section>
              )}

              {/* New Releases Section */}
              {newReleases.length > 0 && (
                <section className="space-y-4">
                  <SectionHeader
                    icon={Clock}
                    title="New Releases"
                    subtitle="Fresh arrivals in the store"
                  />
                  <StoreBookGrid
                    books={newReleases}
                    columns={4}
                    showEmptyState={false}
                  />
                </section>
              )}

              {/* Best Sellers Section */}
              {bestSellers.length > 0 && (
                <section className="space-y-4">
                  <SectionHeader
                    icon={TrendingUp}
                    title="Best Sellers"
                    subtitle="Most popular audiobooks"
                  />
                  <StoreBookGrid
                    books={bestSellers}
                    columns={4}
                    showEmptyState={false}
                  />
                </section>
              )}

              {/* All Books Section */}
              <section className="space-y-4">
                <SectionHeader
                  icon={Filter}
                  title="All Audiobooks"
                  subtitle={`Browse all ${allFilteredBooks.length} titles`}
                />
                <StoreBookGrid />
              </section>
            </div>
          )}
        </>
      )}
    </div>
  )
}
