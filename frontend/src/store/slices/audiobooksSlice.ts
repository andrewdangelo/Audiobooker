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
import { audiobookService } from '@/services/audiobook.service'

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
  status?: 'draft' | 'processing' | 'completed' | 'failed'
  // User-specific data
  progress?: number
  lastPlayedAt?: string
  isBookmarked?: boolean
  // Premium (theatrical) edition info
  isPremium?: boolean          // true = theatrical edition with per-character voices
  purchaseType?: 'basic' | 'premium'  // how the user acquired this book
  conversion?: AudiobookConversion | null
}

export interface AudiobookChapter {
  id: string
  title: string
  startTime: number
  duration: number
}

export type ConversionCreditType = 'basic' | 'premium'
export type ConversionStage = 'configuring' | 'queued' | 'converting'

export interface ConversionVoiceOption {
  id: string
  name: string
  style: string
  accent?: string
  description: string
  sampleLine: string
  recommendedFor?: string
}

export interface ConversionCharacter {
  id: string
  name: string
  role: string
  summary: string
  suggestedVoiceId: string
  selectedVoiceId: string
}

export interface ConversionMetadata {
  title: string
  author: string
  description: string
  genre: string
  language: string
  pageCount: number
  estimatedDurationMinutes: number
  toneTags: string[]
  hook: string
  chaptersPreview: string[]
  characters: Array<{
    id: string
    name: string
    role: string
    summary: string
  }>
}

export interface AudiobookConversion {
  uploadId?: string
  creditType: ConversionCreditType
  stage: ConversionStage
  sourceFileName: string
  sourceFileSize: number
  metadata: ConversionMetadata
  narratorOptions: ConversionVoiceOption[]
  selectedNarratorId: string
  suggestedNarratorId: string
  characters: ConversionCharacter[]
  progress: number
  currentStep: string
  etaLabel: string
  submittedAt?: string
  lastUpdatedAt?: string
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

      const userId = (state as RootState & { auth?: { user?: { id?: string } } }).auth?.user?.id
      if (!userId) throw new Error('Not authenticated')

      // Fetch from backend via API proxy
      const books = await audiobookService.getAll(userId)
      return books
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch audiobooks',
      )
    }
  }
)

export const fetchAudiobookById = createAsyncThunk(
  'audiobooks/fetchById',
  async (id: string, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState

      // Return cached data if it has full detail (chapters present)
      const cached = state.audiobooks.items[id]
      if (
        cached &&
        (
          (Array.isArray(cached.chapters) && cached.chapters.length > 0) ||
          Boolean(cached.conversion)
        )
      ) {
        return cached
      }

      const userId = (state as RootState & { auth?: { user?: { id?: string } } }).auth?.user?.id
      if (!userId) throw new Error('Not authenticated')

      // Fetch from backend via API proxy
      const book = await audiobookService.getById(id, userId)
      return book
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : `Failed to fetch audiobook: ${id}`,
      )
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
    clearAudiobooksError: (state) => {
      state.error = null
    },

    setNarratorSelection: (state, action: PayloadAction<{ id: string; voiceId: string }>) => {
      const book = state.items[action.payload.id]
      if (book?.conversion) {
        book.conversion.selectedNarratorId = action.payload.voiceId
        book.narrator = book.conversion.narratorOptions.find(
          voice => voice.id === action.payload.voiceId,
        )?.name ?? book.narrator
        book.updatedAt = new Date().toISOString()
      }
    },

    setCharacterVoiceSelection: (
      state,
      action: PayloadAction<{ id: string; characterId: string; voiceId: string }>,
    ) => {
      const book = state.items[action.payload.id]
      const character = book?.conversion?.characters.find(
        item => item.id === action.payload.characterId,
      )

      if (book?.conversion && character) {
        character.selectedVoiceId = action.payload.voiceId
        book.updatedAt = new Date().toISOString()
      }
    },

    startMockConversion: (state, action: PayloadAction<string>) => {
      const book = state.items[action.payload]
      if (!book?.conversion) return

      // TODO(back-end): Replace this optimistic local transition with an async thunk
      // that POSTs the chosen credit type, narrator, and character assignments to
      // the API proxy and stores the conversion job id returned by the backend.
      book.status = 'processing'
      book.progress = 0
      book.conversion.stage = 'queued'
      book.conversion.progress = 14
      book.conversion.currentStep = 'Queued for conversion orchestration'
      book.conversion.etaLabel = book.conversion.creditType === 'premium'
        ? 'Estimated 18-24 minutes'
        : 'Estimated 8-12 minutes'
      book.conversion.submittedAt = new Date().toISOString()
      book.conversion.lastUpdatedAt = new Date().toISOString()
      book.updatedAt = new Date().toISOString()
    },

    tickMockConversions: (state) => {
      state.ids.forEach((id) => {
        const book = state.items[id]
        if (!book?.conversion) return
        if (book.conversion.stage !== 'queued' && book.conversion.stage !== 'converting') return

        const increment = book.conversion.creditType === 'premium' ? 4 : 7
        const nextProgress = Math.min(book.conversion.progress + increment, 88)
        book.status = 'processing'
        book.conversion.progress = nextProgress
        book.progress = nextProgress
        book.conversion.stage = nextProgress >= 28 ? 'converting' : 'queued'
        book.conversion.currentStep =
          nextProgress >= 72
            ? 'Packaging chapters and waiting for conversion callback'
            : nextProgress >= 50
              ? 'Rendering chapter audio and smoothing narration'
              : nextProgress >= 28
                ? 'Building the voice plan and chapter batches'
                : 'Queued for conversion orchestration'
        book.conversion.etaLabel =
          nextProgress >= 72
            ? 'Waiting on final backend status'
            : nextProgress >= 50
              ? 'Estimated 4-6 minutes remaining'
              : nextProgress >= 28
                ? 'Estimated 10-14 minutes remaining'
                : book.conversion.creditType === 'premium'
                  ? 'Estimated 18-24 minutes'
                  : 'Estimated 8-12 minutes'
        book.conversion.lastUpdatedAt = new Date().toISOString()
        book.updatedAt = new Date().toISOString()
      })
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
            // Merge: preserve detailed fields (chapters, description, etc.) if already cached
            if (state.items[book.id]) {
              state.items[book.id] = { ...state.items[book.id], ...book }
            } else {
              state.items[book.id] = book
            }
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
  clearAudiobooksError,
  setNarratorSelection,
  setCharacterVoiceSelection,
  startMockConversion,
  tickMockConversions,
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

// Select only premium (theatrical) library books
export const selectPremiumLibraryBooks = (state: RootState): Audiobook[] =>
  selectAllAudiobooks(state).filter(book => book.purchaseType === 'premium' || book.isPremium)

// Select only basic library books
export const selectBasicLibraryBooks = (state: RootState): Audiobook[] =>
  selectAllAudiobooks(state).filter(book => !book.isPremium || book.purchaseType === 'basic')

// Select uploaded books that are still in setup or processing
export const selectConversionFlowBooks = (state: RootState): Audiobook[] =>
  selectAllAudiobooks(state).filter(book => Boolean(book.conversion))

export const selectConfiguringBooks = (state: RootState): Audiobook[] =>
  selectConversionFlowBooks(state).filter(book => book.conversion?.stage === 'configuring')

export const selectProcessingBooks = (state: RootState): Audiobook[] =>
  selectConversionFlowBooks(state).filter(
    book => book.conversion?.stage === 'queued' || book.conversion?.stage === 'converting',
  )

export default audiobooksSlice.reducer
