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
// MOCK DATA (Replace with API calls in production)
// ============================================================================

/**
 * Mock store books for demonstration
 * 
 * TODO: API INTEGRATION
 * Replace this mock data with actual API calls:
 * 
 * Example API call:
 * ```typescript
 * const response = await fetch(`${API_BASE_URL}/store/books`)
 * const data = await response.json()
 * return data.books
 * ```
 */
const mockStoreBooks: StoreBook[] = [
  {
    id: 'store-atomic-habits',
    title: 'Atomic Habits',
    author: 'James Clear',
    description: 'An easy & proven way to build good habits & break bad ones. Learn how tiny changes can lead to remarkable results. James Clear reveals practical strategies that will teach you exactly how to form good habits, break bad ones, and master the tiny behaviors that lead to remarkable results.',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1655988385i/40121378.jpg',
    duration: 19800, // 5.5 hours
    narrator: 'James Clear',
    publishedYear: 2018,
    genre: 'Self-Help',
    rating: 4.8,
    reviewCount: 125432,
    price: 2499, // $24.99
    credits: 1,
    originalPrice: 3499,
    isOnSale: true,
    language: 'English',
    releaseDate: '2018-10-16',
    publisher: 'Penguin Audio',
    tags: ['productivity', 'habits', 'self-improvement', 'psychology'],
  },
  {
    id: 'store-project-hail-mary',
    title: 'Project Hail Mary',
    author: 'Andy Weir',
    description: 'Ryland Grace is the sole survivor on a desperate, last-chance mission—and if he fails, humanity and the earth itself will perish. Except that right now, he doesn\'t know that. He can\'t even remember his own name, let alone the nature of his assignment or how to complete it.',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1597695864i/54493401.jpg',
    duration: 57600, // 16 hours
    narrator: 'Ray Porter',
    publishedYear: 2021,
    genre: 'Science Fiction',
    rating: 4.9,
    reviewCount: 89234,
    price: 2999, // $29.99
    credits: 1,
    language: 'English',
    releaseDate: '2021-05-04',
    publisher: 'Audible Studios',
    tags: ['space', 'survival', 'science', 'adventure'],
  },
  {
    id: 'store-dune',
    title: 'Dune',
    author: 'Frank Herbert',
    description: 'Set on the desert planet Arrakis, Dune is the story of the boy Paul Atreides, heir to a noble family tasked with ruling an inhospitable world where the only thing of value is the "spice" melange, a drug capable of extending life and enhancing consciousness.',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1555447414i/44767458.jpg',
    duration: 75600, // 21 hours
    narrator: 'Scott Brick',
    publishedYear: 1965,
    genre: 'Science Fiction',
    rating: 4.7,
    reviewCount: 156789,
    price: 3499, // $34.99
    credits: 1,
    language: 'English',
    releaseDate: '2007-07-03',
    publisher: 'Macmillan Audio',
    series: 'Dune',
    seriesNumber: 1,
    tags: ['epic', 'politics', 'desert', 'chosen one'],
  },
  {
    id: 'store-educated',
    title: 'Educated',
    author: 'Tara Westover',
    description: 'A memoir about a young girl who, kept out of school, leaves her survivalist family and goes on to earn a PhD from Cambridge University. An unforgettable memoir about a young woman who, kept out of school, leaves her survivalist family and goes on to earn a PhD from Cambridge University.',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1506026635i/35133922.jpg',
    duration: 43200, // 12 hours
    narrator: 'Julia Whelan',
    publishedYear: 2018,
    genre: 'Memoir',
    rating: 4.5,
    reviewCount: 203456,
    price: 1999, // $19.99
    credits: 1,
    language: 'English',
    releaseDate: '2018-02-20',
    publisher: 'Random House Audio',
    tags: ['education', 'family', 'survival', 'inspiring'],
  },
  {
    id: 'store-thinking-fast-slow',
    title: 'Thinking, Fast and Slow',
    author: 'Daniel Kahneman',
    description: 'Nobel Prize winner Daniel Kahneman takes us on a groundbreaking tour of the mind and explains the two systems that drive the way we think. System 1 is fast, intuitive, and emotional; System 2 is slower, more deliberative, and more logical.',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1317793965i/11468377.jpg',
    duration: 72000, // 20 hours
    narrator: 'Patrick Egan',
    publishedYear: 2011,
    genre: 'Psychology',
    rating: 4.4,
    reviewCount: 178234,
    price: 2799, // $27.99
    credits: 1,
    language: 'English',
    releaseDate: '2011-10-25',
    publisher: 'Random House Audio',
    tags: ['psychology', 'decision-making', 'economics', 'behavioral science'],
  },
  {
    id: 'store-the-midnight-library',
    title: 'The Midnight Library',
    author: 'Matt Haig',
    description: 'Between life and death there is a library, and within that library, the shelves go on forever. Every book provides a chance to try another life you could have lived. To see how things would be if you had made other choices... Would you have done anything different, if you had the chance to undo your regrets?',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1602190253i/52578297.jpg',
    duration: 28800, // 8 hours
    narrator: 'Carey Mulligan',
    publishedYear: 2020,
    genre: 'Fiction',
    rating: 4.3,
    reviewCount: 145678,
    price: 2299, // $22.99
    credits: 1,
    originalPrice: 2799,
    isOnSale: true,
    language: 'English',
    releaseDate: '2020-09-29',
    publisher: 'Penguin Audio',
    tags: ['philosophy', 'choices', 'depression', 'hope'],
  },
  {
    id: 'store-sapiens',
    title: 'Sapiens: A Brief History of Humankind',
    author: 'Yuval Noah Harari',
    description: 'From a renowned historian comes a groundbreaking narrative of humanity\'s creation and evolution—a #1 international bestseller—that explores the ways in which biology and history have defined us and enhanced our understanding of what it means to be "human."',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1595674533i/23692271.jpg',
    duration: 54000, // 15 hours
    narrator: 'Derek Perkins',
    publishedYear: 2015,
    genre: 'History',
    rating: 4.6,
    reviewCount: 234567,
    price: 3199, // $31.99
    credits: 1,
    language: 'English',
    releaseDate: '2015-02-10',
    publisher: 'HarperAudio',
    tags: ['history', 'anthropology', 'evolution', 'humanity'],
  },
  {
    id: 'store-fourth-wing',
    title: 'Fourth Wing',
    author: 'Rebecca Yarros',
    description: 'Twenty-year-old Violet Sorrengail was supposed to enter the Scribe Quadrant, living a quiet life among books and history. Now, the commanding general—also known as her tough-as-talons mother—has ordered Violet to join the hundreds of candidates striving to become the elite of Navarre: dragon riders.',
    coverImage: 'https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1701980900i/61431922.jpg',
    duration: 72000, // 20 hours
    narrator: 'Rebecca Soler & Teddy Hamilton',
    publishedYear: 2023,
    genre: 'Fantasy',
    rating: 4.7,
    reviewCount: 89012,
    price: 2899, // $28.99
    credits: 1,
    language: 'English',
    releaseDate: '2023-05-02',
    publisher: 'Recorded Books',
    series: 'The Empyrean',
    seriesNumber: 1,
    tags: ['dragons', 'romance', 'military', 'academy'],
  },
]

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
 * Fetch all store books
 * 
 * TODO: API INTEGRATION
 * Replace the mock data section with an actual API call:
 * 
 * ```typescript
 * // Import your API service
 * import { storeService } from '@/services/store.service'
 * 
 * // Make the API call
 * const response = await storeService.getStoreBooks({
 *   page: state.store.currentPage,
 *   limit: state.store.itemsPerPage,
 *   search: state.store.searchQuery,
 *   filters: state.store.activeFilters,
 *   sortBy: state.store.sortBy,
 *   sortOrder: state.store.sortOrder,
 * })
 * return response.data
 * ```
 */
export const fetchStoreBooks = createAsyncThunk(
  'store/fetchBooks',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const { lastFetched, cacheExpiry } = state.store

      // Return cached data if still valid
      if (lastFetched && Date.now() - lastFetched < cacheExpiry) {
        return null // Signal to use cached data
      }

      // ========================================
      // TODO: Replace with actual API call
      // ========================================
      // Example:
      // const response = await fetch(`${API_BASE_URL}/store/books`)
      // if (!response.ok) throw new Error('Failed to fetch store books')
      // const data = await response.json()
      // return data
      // ========================================

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800))
      
      return {
        books: mockStoreBooks,
        featured: ['store-atomic-habits', 'store-project-hail-mary'],
        newReleases: ['store-fourth-wing', 'store-the-midnight-library'],
        bestSellers: ['store-sapiens', 'store-dune'],
        total: mockStoreBooks.length,
      }
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch store books'
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

      // ========================================
      // TODO: Replace with actual API call
      // ========================================
      // const response = await fetch(`${API_BASE_URL}/store/books/${bookId}`)
      // if (!response.ok) throw new Error('Book not found')
      // return await response.json()
      // ========================================

      await new Promise(resolve => setTimeout(resolve, 300))
      const book = mockStoreBooks.find(b => b.id === bookId)
      
      if (!book) {
        throw new Error('Book not found')
      }
      
      return book
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch book details'
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
      
      if (!book) {
        throw new Error('Book not found')
      }

      if (useCredits && state.store.userCredits < book.credits) {
        throw new Error('Insufficient credits')
      }

      // ========================================
      // TODO: Replace with actual API call
      // ========================================
      // const response = await fetch(`${API_BASE_URL}/store/purchase`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ bookId, useCredits }),
      // })
      // if (!response.ok) throw new Error('Purchase failed')
      // return await response.json()
      // ========================================

      await new Promise(resolve => setTimeout(resolve, 500))
      
      return {
        bookId,
        creditsUsed: useCredits ? book.credits : 0,
        amountCharged: useCredits ? 0 : book.price,
      }
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Purchase failed'
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
