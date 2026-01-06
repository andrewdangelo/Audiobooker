/**
 * UI Slice
 * 
 * Manages UI state like modals, sidebars, themes, and notifications.
 * Not persisted - resets on page reload.
 * 
 * @author Andrew D'Angelo
 * 
 * HOW TO USE:
 * - Import actions: import { openModal, toggleSidebar, addNotification } from '@/store'
 * - Import selectors: import { selectIsSidebarOpen, selectActiveModal } from '@/store'
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'

// Types
export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  description?: string
  duration?: number
}

export interface Modal {
  id: string
  props?: Record<string, unknown>
}

export interface UIState {
  // Sidebar state
  isSidebarOpen: boolean
  isSidebarCollapsed: boolean
  
  // Modal state
  activeModal: Modal | null
  modalHistory: Modal[]
  
  // Theme
  theme: 'light' | 'dark' | 'system'
  
  // Toasts/Notifications
  toasts: Toast[]
  
  // Global loading overlay
  isGlobalLoading: boolean
  globalLoadingMessage?: string
  
  // Mobile menu
  isMobileMenuOpen: boolean
  
  // Search
  isSearchOpen: boolean
  
  // Player
  isPlayerMinimized: boolean
}

// Initial state
const initialState: UIState = {
  isSidebarOpen: true,
  isSidebarCollapsed: false,
  activeModal: null,
  modalHistory: [],
  theme: 'system',
  toasts: [],
  isGlobalLoading: false,
  globalLoadingMessage: undefined,
  isMobileMenuOpen: false,
  isSearchOpen: false,
  isPlayerMinimized: false,
}

// Helper to generate toast ID
const generateToastId = () => `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

// Slice
const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // Sidebar
    toggleSidebar: (state) => {
      state.isSidebarOpen = !state.isSidebarOpen
    },
    
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.isSidebarOpen = action.payload
    },
    
    toggleSidebarCollapsed: (state) => {
      state.isSidebarCollapsed = !state.isSidebarCollapsed
    },
    
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.isSidebarCollapsed = action.payload
    },
    
    // Modal
    openModal: (state, action: PayloadAction<Modal>) => {
      if (state.activeModal) {
        state.modalHistory.push(state.activeModal)
      }
      state.activeModal = action.payload
    },
    
    closeModal: (state) => {
      const previousModal = state.modalHistory.pop()
      state.activeModal = previousModal || null
    },
    
    closeAllModals: (state) => {
      state.activeModal = null
      state.modalHistory = []
    },
    
    // Theme
    setTheme: (state, action: PayloadAction<'light' | 'dark' | 'system'>) => {
      state.theme = action.payload
    },
    
    // Toasts
    addToast: (state, action: PayloadAction<Omit<Toast, 'id'>>) => {
      const toast: Toast = {
        ...action.payload,
        id: generateToastId(),
      }
      state.toasts.push(toast)
    },
    
    removeToast: (state, action: PayloadAction<string>) => {
      state.toasts = state.toasts.filter(t => t.id !== action.payload)
    },
    
    clearAllToasts: (state) => {
      state.toasts = []
    },
    
    // Global loading
    setGlobalLoading: (state, action: PayloadAction<{ isLoading: boolean; message?: string }>) => {
      state.isGlobalLoading = action.payload.isLoading
      state.globalLoadingMessage = action.payload.message
    },
    
    // Mobile menu
    toggleMobileMenu: (state) => {
      state.isMobileMenuOpen = !state.isMobileMenuOpen
    },
    
    setMobileMenuOpen: (state, action: PayloadAction<boolean>) => {
      state.isMobileMenuOpen = action.payload
    },
    
    // Search
    toggleSearch: (state) => {
      state.isSearchOpen = !state.isSearchOpen
    },
    
    setSearchOpen: (state, action: PayloadAction<boolean>) => {
      state.isSearchOpen = action.payload
    },
    
    // Player
    togglePlayerMinimized: (state) => {
      state.isPlayerMinimized = !state.isPlayerMinimized
    },
    
    setPlayerMinimized: (state, action: PayloadAction<boolean>) => {
      state.isPlayerMinimized = action.payload
    },
  },
})

// Export actions
export const {
  toggleSidebar,
  setSidebarOpen,
  toggleSidebarCollapsed,
  setSidebarCollapsed,
  openModal,
  closeModal,
  closeAllModals,
  setTheme,
  addToast,
  removeToast,
  clearAllToasts,
  setGlobalLoading,
  toggleMobileMenu,
  setMobileMenuOpen,
  toggleSearch,
  setSearchOpen,
  togglePlayerMinimized,
  setPlayerMinimized,
} = uiSlice.actions

// Selectors
export const selectIsSidebarOpen = (state: RootState) => state.ui.isSidebarOpen
export const selectIsSidebarCollapsed = (state: RootState) => state.ui.isSidebarCollapsed
export const selectActiveModal = (state: RootState) => state.ui.activeModal
export const selectTheme = (state: RootState) => state.ui.theme
export const selectToasts = (state: RootState) => state.ui.toasts
export const selectIsGlobalLoading = (state: RootState) => state.ui.isGlobalLoading
export const selectGlobalLoadingMessage = (state: RootState) => state.ui.globalLoadingMessage
export const selectIsMobileMenuOpen = (state: RootState) => state.ui.isMobileMenuOpen
export const selectIsSearchOpen = (state: RootState) => state.ui.isSearchOpen
export const selectIsPlayerMinimized = (state: RootState) => state.ui.isPlayerMinimized

export default uiSlice.reducer
