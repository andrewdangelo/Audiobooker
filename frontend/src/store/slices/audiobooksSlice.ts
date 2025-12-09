/**
 * Audiobooks Slice
 * 
 * Manages the audiobook library including fetching, caching, and CRUD operations.
 * Implements caching to reduce API calls and improve performance.
 * 
 * @author Andrew D'Angelo
 * 
 * HOW TO USE:
 * - Import actions: import { fetchAudiobooks, addAudiobook } from '@/store'
 * - Import selectors: import { selectAllAudiobooks, selectAudiobookById } from '@/store'
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'
import { demoBooks, DemoBook } from '@/data/demoBooks'

// Types
export interface Audiobook {
  id: string
  title: string
  author: string
  description?: string
  coverImage?: string
  duration: number
  audioUrl: string
  narrator?: string
  publishedYear?: number
  genre?: string
  chapters?: AudiobookChapter[]
  createdAt?: string
  updatedAt?: string
  // User-specific data
  progress?: number
  lastPlayedAt?: string
  isBookmarked?: boolean
}

export interface AudiobookChapter {
  id: string
  title: string
  startTime: number
  duration: number
}

export interface AudiobooksState {
  // All audiobooks (cached)
  items: Record<string, Audiobook>
  ids: string[]
  
  // Loading states
  loading: boolean
  loadingIds: string[]
  
  // Error state
  error: string | null
  
  // Cache metadata
  lastFetched: number | null
  cacheExpiry: number // milliseconds
  
  // Filters and search
  searchQuery: string
  activeFilters: {
    genre?: string
    author?: string
  }
  sortBy: 'title' | 'author' | 'createdAt' | 'lastPlayed'
  sortOrder: 'asc' | 'desc'
}

// Initial state
const initialState: AudiobooksState = {
  items: {},
  ids: [],
  loading: false,
  loadingIds: [],
  error: null,
  lastFetched: null,
  cacheExpiry: 5 * 60 * 1000, // 5 minutes
  searchQuery: '',
  activeFilters: {},
  sortBy: 'title',
  sortOrder: 'asc',
}

// Helper to convert DemoBook to Audiobook
const convertDemoBook = (book: DemoBook): Audiobook => ({
  id: book.id,
  title: book.title,
  author: book.author,
  description: book.description,
  coverImage: book.coverImage,
  duration: book.duration,
  audioUrl: book.audioUrl,
  narrator: book.narrator,
  publishedYear: book.publishedYear,
  genre: book.genre,
  chapters: book.chapters,
})

// Async thunks
export const fetchAudiobooks = createAsyncThunk(
  'audiobooks/fetchAll',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const { lastFetched, cacheExpiry } = state.audiobooks
      
      // Return cached data if still valid
      if (lastFetched && Date.now() - lastFetched < cacheExpiry) {
        return null // Signal to use cached data
      }
      
      // TODO: Replace with actual API call
      // const response = await audiobookService.getAll()
      // return response.data
      
      // Use demo books for now
      await new Promise(resolve => setTimeout(resolve, 500))
      return demoBooks.map(convertDemoBook)
    } catch (error) {
      return rejectWithValue('Failed to fetch audiobooks')
    }
  }
)

export const fetchAudiobookById = createAsyncThunk(
  'audiobooks/fetchById',
  async (id: string, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      
      // Return cached data if available
      if (state.audiobooks.items[id]) {
        return state.audiobooks.items[id]
      }
      
      // TODO: Replace with actual API call
      // const response = await audiobookService.getById(id)
      // return response.data
      
      // Find in demo books
      const demoBook = demoBooks.find(b => b.id === id)
      if (demoBook) {
        await new Promise(resolve => setTimeout(resolve, 300))
        return convertDemoBook(demoBook)
      }
      
      throw new Error('Audiobook not found')
    } catch (error) {
      return rejectWithValue(`Failed to fetch audiobook: ${id}`)
    }
  }
)

// Slice
const audiobooksSlice = createSlice({
  name: 'audiobooks',
  initialState,
  reducers: {
    // Add a single audiobook to cache
    addAudiobook: (state, action: PayloadAction<Audiobook>) => {
      const book = action.payload
      state.items[book.id] = book
      if (!state.ids.includes(book.id)) {
        state.ids.push(book.id)
      }
    },
    
    // Update an audiobook
    updateAudiobook: (state, action: PayloadAction<{ id: string; updates: Partial<Audiobook> }>) => {
      const { id, updates } = action.payload
      if (state.items[id]) {
        state.items[id] = { ...state.items[id], ...updates }
      }
    },
    
    // Remove an audiobook
    removeAudiobook: (state, action: PayloadAction<string>) => {
      const id = action.payload
      delete state.items[id]
      state.ids = state.ids.filter(i => i !== id)
    },
    
    // Update progress for an audiobook
    updateProgress: (state, action: PayloadAction<{ id: string; progress: number }>) => {
      const { id, progress } = action.payload
      if (state.items[id]) {
        state.items[id].progress = progress
        state.items[id].lastPlayedAt = new Date().toISOString()
      }
    },
    
    // Toggle bookmark
    toggleBookmark: (state, action: PayloadAction<string>) => {
      const id = action.payload
      if (state.items[id]) {
        state.items[id].isBookmarked = !state.items[id].isBookmarked
      }
    },
    
    // Search and filter
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload
    },
    
    setFilter: (state, action: PayloadAction<{ key: 'genre' | 'author'; value: string | undefined }>) => {
      const { key, value } = action.payload
      if (value) {
        state.activeFilters[key] = value
      } else {
        delete state.activeFilters[key]
      }
    },
    
    clearFilters: (state) => {
      state.activeFilters = {}
      state.searchQuery = ''
    },
    
    // Sorting
    setSorting: (state, action: PayloadAction<{ sortBy: AudiobooksState['sortBy']; sortOrder: AudiobooksState['sortOrder'] }>) => {
      state.sortBy = action.payload.sortBy
      state.sortOrder = action.payload.sortOrder
    },
    
    // Clear cache
    clearCache: (state) => {
      state.items = {}
      state.ids = []
      state.lastFetched = null
    },
    
    // Clear error
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch all
      .addCase(fetchAudiobooks.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchAudiobooks.fulfilled, (state, action) => {
        state.loading = false
        if (action.payload) {
          // Update cache with new data
          action.payload.forEach(book => {
            state.items[book.id] = book
            if (!state.ids.includes(book.id)) {
              state.ids.push(book.id)
            }
          })
          state.lastFetched = Date.now()
        }
      })
      .addCase(fetchAudiobooks.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Fetch by ID
      .addCase(fetchAudiobookById.pending, (state, action) => {
        state.loadingIds.push(action.meta.arg)
      })
      .addCase(fetchAudiobookById.fulfilled, (state, action) => {
        state.loadingIds = state.loadingIds.filter(id => id !== action.meta.arg)
        if (action.payload) {
          state.items[action.payload.id] = action.payload
          if (!state.ids.includes(action.payload.id)) {
            state.ids.push(action.payload.id)
          }
        }
      })
      .addCase(fetchAudiobookById.rejected, (state, action) => {
        state.loadingIds = state.loadingIds.filter(id => id !== action.meta.arg)
        state.error = action.payload as string
      })
  },
})

// Export actions
export const {
  addAudiobook,
  updateAudiobook,
  removeAudiobook,
  updateProgress,
  toggleBookmark,
  setSearchQuery,
  setFilter,
  clearFilters,
  setSorting,
  clearCache,
  clearError,
} = audiobooksSlice.actions

// Selectors
export const selectAllAudiobooks = (state: RootState): Audiobook[] => 
  state.audiobooks.ids.map((id: string) => state.audiobooks.items[id])

export const selectAudiobookById = (state: RootState, id: string): Audiobook | undefined => 
  state.audiobooks.items[id]

export const selectAudiobooksLoading = (state: RootState) => state.audiobooks.loading
export const selectAudiobooksError = (state: RootState) => state.audiobooks.error
export const selectSearchQuery = (state: RootState) => state.audiobooks.searchQuery
export const selectActiveFilters = (state: RootState) => state.audiobooks.activeFilters
export const selectSortBy = (state: RootState) => state.audiobooks.sortBy
export const selectSortOrder = (state: RootState) => state.audiobooks.sortOrder

// Filtered and sorted selector
export const selectFilteredAudiobooks = (state: RootState): Audiobook[] => {
  let books = selectAllAudiobooks(state)
  const { searchQuery, activeFilters, sortBy, sortOrder } = state.audiobooks
  
  // Apply search filter
  if (searchQuery) {
    const query = searchQuery.toLowerCase()
    books = books.filter(book => 
      book.title.toLowerCase().includes(query) ||
      book.author.toLowerCase().includes(query) ||
      book.description?.toLowerCase().includes(query)
    )
  }
  
  // Apply genre filter
  if (activeFilters.genre) {
    books = books.filter(book => book.genre === activeFilters.genre)
  }
  
  // Apply author filter
  if (activeFilters.author) {
    books = books.filter(book => book.author === activeFilters.author)
  }
  
  // Sort
  books.sort((a, b) => {
    let comparison = 0
    switch (sortBy) {
      case 'title':
        comparison = a.title.localeCompare(b.title)
        break
      case 'author':
        comparison = a.author.localeCompare(b.author)
        break
      case 'createdAt':
        comparison = (a.createdAt || '').localeCompare(b.createdAt || '')
        break
      case 'lastPlayed':
        comparison = (a.lastPlayedAt || '').localeCompare(b.lastPlayedAt || '')
        break
    }
    return sortOrder === 'asc' ? comparison : -comparison
  })
  
  return books
}

// Select bookmarked audiobooks
export const selectBookmarkedAudiobooks = (state: RootState): Audiobook[] =>
  selectAllAudiobooks(state).filter(book => book.isBookmarked)

// Select recently played audiobooks
export const selectRecentlyPlayed = (state: RootState): Audiobook[] =>
  selectAllAudiobooks(state)
    .filter(book => book.lastPlayedAt)
    .sort((a, b) => (b.lastPlayedAt || '').localeCompare(a.lastPlayedAt || ''))
    .slice(0, 10)

// Select audiobooks with progress
export const selectInProgressAudiobooks = (state: RootState): Audiobook[] =>
  selectAllAudiobooks(state)
    .filter(book => book.progress && book.progress > 0 && book.progress < 100)

export default audiobooksSlice.reducer
