/**
 * Store Slice
 * 
 * Manages the audiobook store/marketplace state including:
 * - Store catalog (available books for purchase)
 * - Pricing and credits
 * - Search and filtering
 * - Purchase flow
 * 
 * @author Andrew D'Angelo
 * 
 * HOW TO USE:
 * - Import actions: import { fetchStoreBooks, purchaseBook } from '@/store'
 * - Import selectors: import { selectStoreBooks, selectStoreBooksLoading } from '@/store'
 * 
 * API INTEGRATION POINTS:
 * - fetchStoreBooks: Replace mock data with API call to get store catalog
 * - fetchBookDetails: Replace with API call to get full book details
 * - purchaseBook: Replace with API call to process purchase
 * - searchStoreBooks: Can be client-side or server-side search
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'
import { storeService } from '@/services/backendService'
import { paymentService } from '@/services/paymentService'

// ============================================================================
// TYPES
// ============================================================================

/**
 * Store book item - represents an audiobook available for purchase
 * This extends the basic audiobook with pricing and store-specific metadata
 */
export interface StoreBook {
  id: string
  title: string
  author: string
  description: string
  coverImage?: string
  duration: number // in seconds
  narrator: string
  publishedYear: number
  genre: string
  rating: number // 0-5 scale
  reviewCount: number
  // Pricing
  price: number // in cents (e.g., 1499 = $14.99)
  credits: number // number of credits needed (typically 1)
  originalPrice?: number // for displaying discounts
  isOnSale?: boolean
  // Additional metadata
  language: string
  releaseDate: string
  publisher: string
  series?: string
  seriesNumber?: number
  tags: string[]
  sampleAudioUrl?: string
}

/**
 * Store state shape
 */
export interface StoreState {
  // Store catalog
  books: Record<string, StoreBook>
  bookIds: string[]
  
  // Featured/promoted content
  featuredBookIds: string[]
  newReleaseIds: string[]
  bestSellerIds: string[]
  
  // Loading states
  loading: boolean
  loadingBookId: string | null
  
  // Error state
  error: string | null
  
  // Cache metadata
  lastFetched: number | null
  cacheExpiry: number // milliseconds
  
  // Search and filters
  searchQuery: string
  activeFilters: StoreFilters
  sortBy: StoreSortOption
  sortOrder: 'asc' | 'desc'
  
  // Pagination
  currentPage: number
  itemsPerPage: number
  totalItems: number
  
  // User's credits (for purchase flow)
  userCredits: number
}

export interface StoreFilters {
  genre?: string
  priceRange?: { min: number; max: number }
  minRating?: number
  language?: string
  narrator?: string
  onSaleOnly?: boolean
}

export type StoreSortOption = 
  | 'relevance' 
  | 'title' 
  | 'author' 
  | 'price-low' 
  | 'price-high' 
  | 'rating' 
  | 'newest' 
  | 'bestselling'

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Maps backend API book response fields to the frontend StoreBook shape.
 * Backend uses snake_case; frontend StoreBook uses camelCase.
 */
function normalizeStoreBook(book: Record<string, unknown>): StoreBook {
  return {
    id: (book.id ?? book._id ?? '') as string,
    title: (book.title ?? '') as string,
    author: (book.author ?? '') as string,
    description: (book.description ?? '') as string,
    coverImage: (book.cover_image_url ?? book.coverImage ?? '') as string,
    duration: (book.duration ?? 0) as number,
    narrator: (book.narrator ?? '') as string,
    publishedYear: (book.published_year ?? book.publishedYear ?? 0) as number,
    genre: (book.genre ?? '') as string,
    rating: (book.rating ?? 0) as number,
    reviewCount: (book.review_count ?? book.reviewCount ?? 0) as number,
    price: (book.price ?? 0) as number,
    credits: (book.credits ?? book.credits_required ?? 1) as number,
    originalPrice: book.original_price as number | undefined,
    isOnSale: book.is_on_sale as boolean | undefined,
    language: (book.language ?? 'English') as string,
    releaseDate: (book.release_date ?? book.releaseDate ?? '') as string,
    publisher: (book.publisher ?? '') as string,
    series: book.series as string | undefined,
    seriesNumber: book.series_number as number | undefined,
    tags: (book.tags ?? []) as string[],
    sampleAudioUrl: (book.sample_audio_url ?? book.sampleAudioUrl) as string | undefined,
  }
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState: StoreState = {
  books: {},
  bookIds: [],
  featuredBookIds: [],
  newReleaseIds: [],
  bestSellerIds: [],
  loading: false,
  loadingBookId: null,
  error: null,
  lastFetched: null,
  cacheExpiry: 5 * 60 * 1000, // 5 minutes
  searchQuery: '',
  activeFilters: {},
  sortBy: 'relevance',
  sortOrder: 'desc',
  currentPage: 1,
  itemsPerPage: 20,
  totalItems: 0,
  userCredits: 3, // Mock user credits
}

// ============================================================================
// ASYNC THUNKS
// ============================================================================

/**
 * Fetch store books (catalog) from the backend microservice via API proxy.
 * Includes parallel fetching of featured, new-release, and bestseller lists.
 */
export const fetchStoreBooks = createAsyncThunk(
  'store/fetchBooks',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const { lastFetched, cacheExpiry, currentPage, itemsPerPage, activeFilters, sortBy } = state.store

      // Return cached data if still valid
      if (lastFetched && Date.now() - lastFetched < cacheExpiry) {
        return null // Signal to use cached data
      }

      // Fetch store catalog from backend via API proxy
      const data = await storeService.getCatalog({
        genre: activeFilters.genre,
        sort: sortBy === 'bestselling' ? 'popular' : sortBy === 'newest' ? 'recent' : 'popular',
        page: currentPage,
        limit: itemsPerPage,
      })

      // Fetch featured, new releases, bestsellers in parallel
      const [featured, newReleases, bestSellers] = await Promise.allSettled([
        storeService.getFeatured(),
        storeService.getNewReleases(),
        storeService.getBestsellers(),
      ])

      return {
        books: (data.books as unknown as Record<string, unknown>[]).map(b => normalizeStoreBook(b)),
        featured: featured.status === 'fulfilled'
          ? (featured.value.books as StoreBook[]).map(b => b.id)
          : [],
        newReleases: newReleases.status === 'fulfilled'
          ? (newReleases.value.books as StoreBook[]).map(b => b.id)
          : [],
        bestSellers: bestSellers.status === 'fulfilled'
          ? (bestSellers.value.books as StoreBook[]).map(b => b.id)
          : [],
        total: data.total,
      }
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch store books',
      )
    }
  }
)

/**
 * Fetch a single book's details
 * 
 * TODO: API INTEGRATION
 * Replace with API call to get full book details including reviews, samples, etc.
 */
export const fetchStoreBookDetails = createAsyncThunk(
  'store/fetchBookDetails',
  async (bookId: string, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState

      // Return cached if available
      if (state.store.books[bookId]) {
        return state.store.books[bookId]
      }

      // Fetch from backend via API proxy
      const book = await storeService.getBookDetails(bookId)
      return normalizeStoreBook(book as unknown as Record<string, unknown>)
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch book details',
      )
    }
  }
)

/**
 * Purchase a book (using credits or payment)
 * 
 * TODO: API INTEGRATION
 * This should connect to your payment/credits system
 */
export const purchaseBook = createAsyncThunk(
  'store/purchaseBook',
  async (
    { bookId, useCredits }: { bookId: string; useCredits: boolean },
    { getState, rejectWithValue }
  ) => {
    try {
      const state = getState() as RootState
      const book = state.store.books[bookId]

      if (!book) throw new Error('Book not found')
      if (useCredits && state.store.userCredits < book.credits) {
        throw new Error('Insufficient credits')
      }

      const userId = (state as RootState & { auth?: { user?: { id?: string } } }).auth?.user?.id
      if (!userId) throw new Error('Not authenticated')

      if (useCredits) {
        // Process via credits through payment service
        const response = await paymentService.payWithCredits({
          user_id: userId,
          items: [
            {
              book_id: bookId,
              quantity: 1,
              price_cents: book.price,
              credits: book.credits,
              title: book.title,
            },
          ],
          currency: 'usd',
          metadata: { book_ids: bookId },
        })
        return {
          bookId,
          creditsUsed: book.credits,
          amountCharged: 0,
          remainingCredits: response.remaining_credits,
        }
      } else {
        // Card purchase — handled by Stripe via payment service (checkout session)
        const response = await storeService.purchase(userId, bookId, 'card')
        return {
          bookId,
          creditsUsed: 0,
          amountCharged: book.price,
          remainingCredits: state.store.userCredits,
          ...response,
        }
      }
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Purchase failed',
      )
    }
  }
)

// ============================================================================
// SLICE
// ============================================================================

const storeSlice = createSlice({
  name: 'store',
  initialState,
  reducers: {
    /**
     * Set search query for filtering store books
     */
    setStoreSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload
      state.currentPage = 1 // Reset to first page on new search
    },

    /**
     * Set active filters
     */
    setStoreFilters: (state, action: PayloadAction<StoreFilters>) => {
      state.activeFilters = action.payload
      state.currentPage = 1
    },

    /**
     * Update a single filter
     */
    updateStoreFilter: (
      state,
      action: PayloadAction<{ key: keyof StoreFilters; value: unknown }>
    ) => {
      const { key, value } = action.payload
      if (value === undefined || value === null || value === '') {
        delete state.activeFilters[key]
      } else {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (state.activeFilters as any)[key] = value
      }
      state.currentPage = 1
    },

    /**
     * Clear all filters
     */
    clearStoreFilters: (state) => {
      state.activeFilters = {}
      state.searchQuery = ''
      state.currentPage = 1
    },

    /**
     * Set sort option
     */
    setStoreSort: (
      state,
      action: PayloadAction<{ sortBy: StoreSortOption; sortOrder?: 'asc' | 'desc' }>
    ) => {
      state.sortBy = action.payload.sortBy
      if (action.payload.sortOrder) {
        state.sortOrder = action.payload.sortOrder
      }
    },

    /**
     * Set current page for pagination
     */
    setStorePage: (state, action: PayloadAction<number>) => {
      state.currentPage = action.payload
    },

    /**
     * Clear error state
     */
    clearStoreError: (state) => {
      state.error = null
    },

    /**
     * Invalidate cache (force refetch on next request)
     */
    invalidateStoreCache: (state) => {
      state.lastFetched = null
    },

    /**
     * Increment user credits by a specific amount
     * Used after successful credit purchase
     */
    incrementUserCredits: (state, action: PayloadAction<number>) => {
      state.userCredits += action.payload
    },

    /**
     * Update user credits to a specific value
     * Used when fetching user profile data
     */
    updateUserCredits: (state, action: PayloadAction<number>) => {
      state.userCredits = action.payload
    },
  },
  extraReducers: (builder) => {
    // Fetch store books
    builder
      .addCase(fetchStoreBooks.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchStoreBooks.fulfilled, (state, action) => {
        state.loading = false
        
        // If null, use cached data (no update needed)
        if (action.payload === null) return

        const { books, featured, newReleases, bestSellers, total } = action.payload
        
        // Normalize books into record
        state.books = {}
        state.bookIds = []
        books.forEach((book: StoreBook) => {
          state.books[book.id] = book
          state.bookIds.push(book.id)
        })
        
        state.featuredBookIds = featured
        state.newReleaseIds = newReleases
        state.bestSellerIds = bestSellers
        state.totalItems = total
        state.lastFetched = Date.now()
      })
      .addCase(fetchStoreBooks.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })

    // Fetch single book details
    builder
      .addCase(fetchStoreBookDetails.pending, (state, action) => {
        state.loadingBookId = action.meta.arg
      })
      .addCase(fetchStoreBookDetails.fulfilled, (state, action) => {
        state.loadingBookId = null
        if (action.payload) {
          state.books[action.payload.id] = action.payload
          if (!state.bookIds.includes(action.payload.id)) {
            state.bookIds.push(action.payload.id)
          }
        }
      })
      .addCase(fetchStoreBookDetails.rejected, (state) => {
        state.loadingBookId = null
      })

    // Purchase book
    builder
      .addCase(purchaseBook.fulfilled, (state, action) => {
        if (action.payload.creditsUsed > 0) {
          state.userCredits -= action.payload.creditsUsed
        }
      })
  },
})

// ============================================================================
// EXPORTS - Actions
// ============================================================================

/**
 * Add credits to user account
 * Called after successful credit purchase
 */
export const addUserCredits = (creditsToAdd: number) => (dispatch: any) => {
  dispatch(storeSlice.actions.incrementUserCredits(creditsToAdd))
}

/**
 * Set user credits to a specific value
 * Called when fetching user profile
 */
export const setUserCredits = (credits: number) => (dispatch: any) => {
  dispatch(storeSlice.actions.updateUserCredits(credits))
}

export const {
  setStoreSearchQuery,
  setStoreFilters,
  updateStoreFilter,
  clearStoreFilters,
  setStoreSort,
  setStorePage,
  clearStoreError,
  invalidateStoreCache,
} = storeSlice.actions

// ============================================================================
// SELECTORS
// ============================================================================

/**
 * Select all store books as an array
 */
export const selectStoreBooks = (state: RootState): StoreBook[] =>
  state.store.bookIds.map((id: string) => state.store.books[id])

/**
 * Select a single store book by ID
 */
export const selectStoreBookById = (state: RootState, bookId: string): StoreBook | undefined =>
  state.store.books[bookId]

/**
 * Select featured books
 */
export const selectFeaturedBooks = (state: RootState): StoreBook[] =>
  state.store.featuredBookIds
    .map((id: string) => state.store.books[id])
    .filter(Boolean)

/**
 * Select new releases
 */
export const selectNewReleases = (state: RootState): StoreBook[] =>
  state.store.newReleaseIds
    .map((id: string) => state.store.books[id])
    .filter(Boolean)

/**
 * Select best sellers
 */
export const selectBestSellers = (state: RootState): StoreBook[] =>
  state.store.bestSellerIds
    .map((id: string) => state.store.books[id])
    .filter(Boolean)

/**
 * Select filtered and sorted store books based on current search/filter state
 */
export const selectFilteredStoreBooks = (state: RootState): StoreBook[] => {
  const { books, bookIds, searchQuery, activeFilters, sortBy, sortOrder } = state.store
  
  let filtered: StoreBook[] = bookIds.map((id: string) => books[id])

  // Apply search filter
  if (searchQuery) {
    const query = searchQuery.toLowerCase()
    filtered = filtered.filter(
      book =>
        book.title.toLowerCase().includes(query) ||
        book.author.toLowerCase().includes(query) ||
        book.narrator.toLowerCase().includes(query) ||
        book.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  // Apply genre filter
  if (activeFilters.genre) {
    filtered = filtered.filter(book => book.genre === activeFilters.genre)
  }

  // Apply price range filter
  if (activeFilters.priceRange) {
    const { min, max } = activeFilters.priceRange
    filtered = filtered.filter(book => book.price >= min && book.price <= max)
  }

  // Apply rating filter
  if (activeFilters.minRating) {
    filtered = filtered.filter(book => book.rating >= activeFilters.minRating!)
  }

  // Apply language filter
  if (activeFilters.language) {
    filtered = filtered.filter(book => book.language === activeFilters.language)
  }

  // Apply on sale filter
  if (activeFilters.onSaleOnly) {
    filtered = filtered.filter(book => book.isOnSale)
  }

  // Sort results
  filtered.sort((a, b) => {
    let comparison = 0
    
    switch (sortBy) {
      case 'title':
        comparison = a.title.localeCompare(b.title)
        break
      case 'author':
        comparison = a.author.localeCompare(b.author)
        break
      case 'price-low':
        comparison = a.price - b.price
        break
      case 'price-high':
        comparison = b.price - a.price
        break
      case 'rating':
        comparison = b.rating - a.rating
        break
      case 'newest':
        comparison = new Date(b.releaseDate).getTime() - new Date(a.releaseDate).getTime()
        break
      case 'bestselling':
        comparison = b.reviewCount - a.reviewCount
        break
      default:
        // relevance - use review count as proxy
        comparison = b.reviewCount - a.reviewCount
    }
    
    return sortOrder === 'asc' ? -comparison : comparison
  })

  return filtered
}

/**
 * Select loading state
 */
export const selectStoreBooksLoading = (state: RootState): boolean =>
  state.store.loading

/**
 * Select error state
 */
export const selectStoreBooksError = (state: RootState): string | null =>
  state.store.error

/**
 * Select search query
 */
export const selectStoreSearchQuery = (state: RootState): string =>
  state.store.searchQuery

/**
 * Select active filters
 */
export const selectStoreFilters = (state: RootState): StoreFilters =>
  state.store.activeFilters

/**
 * Select sort options
 */
export const selectStoreSort = (state: RootState) => ({
  sortBy: state.store.sortBy,
  sortOrder: state.store.sortOrder,
})

/**
 * Select user credits
 */
export const selectUserCredits = (state: RootState): number =>
  state.store.userCredits

/**
 * Select available genres from current store books
 */
export const selectAvailableGenres = (state: RootState): string[] => {
  const genres = new Set<string>()
  state.store.bookIds.forEach((id: string) => {
    const book = state.store.books[id]
    if (book?.genre) genres.add(book.genre)
  })
  return Array.from(genres).sort()
}

/**
 * Select pagination info
 */
export const selectStorePagination = (state: RootState) => ({
  currentPage: state.store.currentPage,
  itemsPerPage: state.store.itemsPerPage,
  totalItems: state.store.totalItems,
  totalPages: Math.ceil(state.store.totalItems / state.store.itemsPerPage),
})

export default storeSlice.reducer
