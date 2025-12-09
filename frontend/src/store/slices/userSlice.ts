/**
 * User Slice
 * 
 * Manages user preferences and settings.
 * Persisted to maintain user preferences across sessions.
 * 
 * @author Andrew D'Angelo
 * 
 * HOW TO USE:
 * - Import actions: import { updatePreferences, addToHistory } from '@/store'
 * - Import selectors: import { selectUserPreferences, selectListeningHistory } from '@/store'
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'

// Types
export interface UserPreferences {
  // Playback preferences
  defaultPlaybackSpeed: number
  defaultVolume: number
  autoPlay: boolean
  skipSilence: boolean
  sleepTimer: number | null // minutes, null = disabled
  
  // Display preferences
  showChapterList: boolean
  showRemainingTime: boolean
  compactPlayerView: boolean
  
  // Notification preferences
  emailNotifications: boolean
  pushNotifications: boolean
  
  // Privacy
  saveListeningHistory: boolean
}

export interface ListeningHistoryEntry {
  audiobookId: string
  timestamp: string
  progress: number
  duration: number
}

export interface UserState {
  preferences: UserPreferences
  listeningHistory: ListeningHistoryEntry[]
  recentSearches: string[]
  favoriteGenres: string[]
}

// Initial state with sensible defaults
const initialState: UserState = {
  preferences: {
    defaultPlaybackSpeed: 1,
    defaultVolume: 0.8,
    autoPlay: true,
    skipSilence: false,
    sleepTimer: null,
    showChapterList: true,
    showRemainingTime: false,
    compactPlayerView: false,
    emailNotifications: true,
    pushNotifications: true,
    saveListeningHistory: true,
  },
  listeningHistory: [],
  recentSearches: [],
  favoriteGenres: [],
}

// Slice
const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    // Update all preferences
    setPreferences: (state, action: PayloadAction<UserPreferences>) => {
      state.preferences = action.payload
    },
    
    // Update specific preference
    updatePreference: <K extends keyof UserPreferences>(
      state: UserState,
      action: PayloadAction<{ key: K; value: UserPreferences[K] }>
    ) => {
      state.preferences[action.payload.key] = action.payload.value
    },
    
    // Reset preferences to defaults
    resetPreferences: (state) => {
      state.preferences = initialState.preferences
    },
    
    // Listening history
    addToHistory: (state, action: PayloadAction<Omit<ListeningHistoryEntry, 'timestamp'>>) => {
      if (!state.preferences.saveListeningHistory) return
      
      const entry: ListeningHistoryEntry = {
        ...action.payload,
        timestamp: new Date().toISOString(),
      }
      
      // Remove existing entry for same audiobook if exists
      state.listeningHistory = state.listeningHistory.filter(
        h => h.audiobookId !== entry.audiobookId
      )
      
      // Add new entry at the beginning
      state.listeningHistory.unshift(entry)
      
      // Keep only last 100 entries
      if (state.listeningHistory.length > 100) {
        state.listeningHistory = state.listeningHistory.slice(0, 100)
      }
    },
    
    clearHistory: (state) => {
      state.listeningHistory = []
    },
    
    removeFromHistory: (state, action: PayloadAction<string>) => {
      state.listeningHistory = state.listeningHistory.filter(
        h => h.audiobookId !== action.payload
      )
    },
    
    // Recent searches
    addRecentSearch: (state, action: PayloadAction<string>) => {
      const search = action.payload.trim()
      if (!search) return
      
      // Remove if already exists
      state.recentSearches = state.recentSearches.filter(s => s !== search)
      
      // Add at beginning
      state.recentSearches.unshift(search)
      
      // Keep only last 10
      if (state.recentSearches.length > 10) {
        state.recentSearches = state.recentSearches.slice(0, 10)
      }
    },
    
    clearRecentSearches: (state) => {
      state.recentSearches = []
    },
    
    // Favorite genres
    addFavoriteGenre: (state, action: PayloadAction<string>) => {
      if (!state.favoriteGenres.includes(action.payload)) {
        state.favoriteGenres.push(action.payload)
      }
    },
    
    removeFavoriteGenre: (state, action: PayloadAction<string>) => {
      state.favoriteGenres = state.favoriteGenres.filter(g => g !== action.payload)
    },
    
    setFavoriteGenres: (state, action: PayloadAction<string[]>) => {
      state.favoriteGenres = action.payload
    },
  },
})

// Export actions
export const {
  setPreferences,
  updatePreference,
  resetPreferences,
  addToHistory,
  clearHistory,
  removeFromHistory,
  addRecentSearch,
  clearRecentSearches,
  addFavoriteGenre,
  removeFavoriteGenre,
  setFavoriteGenres,
} = userSlice.actions

// Selectors
export const selectUserPreferences = (state: RootState) => state.user.preferences
export const selectListeningHistory = (state: RootState) => state.user.listeningHistory
export const selectRecentSearches = (state: RootState) => state.user.recentSearches
export const selectFavoriteGenres = (state: RootState) => state.user.favoriteGenres

// Specific preference selectors
export const selectDefaultPlaybackSpeed = (state: RootState) => state.user.preferences.defaultPlaybackSpeed
export const selectDefaultVolume = (state: RootState) => state.user.preferences.defaultVolume
export const selectAutoPlay = (state: RootState) => state.user.preferences.autoPlay

export default userSlice.reducer
