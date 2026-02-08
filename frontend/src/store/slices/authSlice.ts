/**
 * Authentication Slice
 * 
 * Manages authentication state including login status, tokens, and auth errors.
 * Persisted to localStorage for session continuity.
 * 
 * @author Andrew D'Angelo
 * 
 * HOW TO USE:
 * - Import actions: import { login, logout, setAuthError } from '@/store'
 * - Import selectors: import { selectIsAuthenticated, selectAuthToken } from '@/store'
 * - Dispatch actions: dispatch(login({ token: '...', user: {...} }))
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'
import { authService } from '@/services/authService'
import { setUserCredits } from './storeSlice'
import { setSubscription } from './subscriptionSlice'

// Types - matches API response from auth service
export interface AuthUser {
  id: string
  email: string
  first_name: string
  last_name?: string
  username?: string
  is_active?: boolean
  auth_provider?: string
  avatarUrl?: string
  credits?: number
  basic_credits?: number
  premium_credits?: number
  // Subscription fields
  subscription_plan?: 'none' | 'basic' | 'premium'
  subscription_status?: 'none' | 'active' | 'cancelled' | 'expired' | 'pending_cancellation'
  subscription_billing_cycle?: 'monthly' | 'annual' | null
  subscription_end_date?: string | null
  subscription_discount_applied?: boolean
}

export interface AuthState {
  isAuthenticated: boolean
  user: AuthUser | null
  token: string | null
  refreshToken: string | null
  loading: boolean
  error: string | null
}

// Helper to get display name
export function getUserDisplayName(user: AuthUser | null): string {
  if (!user) return 'User'
  if (user.first_name && user.last_name) {
    return `${user.first_name} ${user.last_name}`
  }
  return user.first_name || user.username || user.email.split('@')[0]
}

// Initial state
const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  token: null,
  refreshToken: null,
  loading: false,
  error: null,
}

// Async thunks for API calls
// TODO: Connect to actual API endpoints
export const loginAsync = createAsyncThunk(
  'auth/login',
  async (credentials: { email: string; password: string }, { rejectWithValue }) => {
    try {
      // TODO: Replace with actual API call
      // const response = await authService.login(credentials)
      // return response.data
      
      // Mock response for development
      await new Promise(resolve => setTimeout(resolve, 1000))
      return {
        token: 'mock-jwt-token',
        refreshToken: 'mock-refresh-token',
        user: {
          id: '1',
          email: credentials.email,
          first_name: 'John',
          last_name: 'Doe',
        }
      }
    } catch (error) {
      return rejectWithValue('Invalid email or password')
    }
  }
)

export const logoutAsync = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      // TODO: Call logout API endpoint
      // await authService.logout()
      return true
    } catch (error) {
      return rejectWithValue('Logout failed')
    }
  }
)

// Fetch user credits from backend and sync with Redux
export const fetchUserCredits = createAsyncThunk(
  'auth/fetchCredits',
  async (_, { dispatch, getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const token = state.auth.token
      
      if (!token) {
        return rejectWithValue('No auth token')
      }
      
      const response = await authService.getUserCredits(token)
      
      // Update store slice with fetched credits (use total_credits)
      dispatch(setUserCredits(response.total_credits))
      
      return response.total_credits
    } catch (error) {
      console.error('Failed to fetch user credits:', error)
      return rejectWithValue('Failed to fetch credits')
    }
  }
)

// Fetch subscription status and sync with Redux
export const fetchUserSubscription = createAsyncThunk(
  'auth/fetchSubscription',
  async (_, { dispatch, getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const token = state.auth.token
      
      if (!token) {
        return rejectWithValue('No auth token')
      }
      
      const response = await authService.getSubscriptionStatus(token)
      
      // Update subscription slice
      dispatch(setSubscription({
        plan: response.subscription_plan,
        status: response.subscription_status,
        billingCycle: response.subscription_billing_cycle,
        currentPeriodEnd: response.subscription_end_date,
        discountApplied: response.subscription_discount_applied,
      }))
      
      return response
    } catch (error) {
      console.error('Failed to fetch subscription status:', error)
      return rejectWithValue('Failed to fetch subscription')
    }
  }
)

// Slice
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    // Synchronous login (for OAuth callbacks, etc.)
    login: (state, action: PayloadAction<{ token: string; user: AuthUser; refreshToken?: string }>) => {
      state.isAuthenticated = true
      state.token = action.payload.token
      state.user = action.payload.user
      state.refreshToken = action.payload.refreshToken || null
      state.error = null
    },
    
    // Logout user
    logout: (state) => {
      state.isAuthenticated = false
      state.user = null
      state.token = null
      state.refreshToken = null
      state.error = null
    },
    
    // Update user profile
    updateUser: (state, action: PayloadAction<Partial<AuthUser>>) => {
      if (state.user) {
        state.user = { ...state.user, ...action.payload }
      }
    },
    
    // Set auth error
    setAuthError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },
    
    // Clear auth error
    clearAuthError: (state) => {
      state.error = null
    },
    
    // Update tokens (for refresh flow)
    updateTokens: (state, action: PayloadAction<{ token: string; refreshToken?: string }>) => {
      state.token = action.payload.token
      if (action.payload.refreshToken) {
        state.refreshToken = action.payload.refreshToken
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Login async
      .addCase(loginAsync.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(loginAsync.fulfilled, (state, action) => {
        state.loading = false
        state.isAuthenticated = true
        state.token = action.payload.token
        state.refreshToken = action.payload.refreshToken
        state.user = action.payload.user
      })
      .addCase(loginAsync.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Logout async
      .addCase(logoutAsync.fulfilled, (state) => {
        state.isAuthenticated = false
        state.user = null
        state.token = null
        state.refreshToken = null
      })
  },
})

// Export actions
export const { 
  login, 
  logout, 
  updateUser, 
  setAuthError, 
  clearAuthError,
  updateTokens 
} = authSlice.actions

// Selectors
export const selectIsAuthenticated = (state: RootState) => state.auth.isAuthenticated
export const selectCurrentUser = (state: RootState) => state.auth.user
export const selectAuthToken = (state: RootState) => state.auth.token
export const selectRefreshToken = (state: RootState) => state.auth.refreshToken
export const selectAuthLoading = (state: RootState) => state.auth.loading
export const selectAuthError = (state: RootState) => state.auth.error
export const selectUserDisplayName = (state: RootState) => getUserDisplayName(state.auth.user)

export default authSlice.reducer
