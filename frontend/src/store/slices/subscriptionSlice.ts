/**
 * Subscription Slice
 * 
 * Manages subscription state including:
 * - Current subscription plan and status
 * - Cancellation flow state
 * - Retention offers
 * 
 * @author Audiobooker Team
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'
import { 
  subscriptionService,
  type SubscriptionPlan,
  type SubscriptionStatus,
  type BillingCycle,
  type CancellationStage,
  type DiscountOffer,
} from '@/services/subscriptionService'

// ============================================================================
// TYPES
// ============================================================================

export interface SubscriptionState {
  // Current subscription
  plan: SubscriptionPlan
  status: SubscriptionStatus
  billingCycle: BillingCycle | null
  currentPeriodEnd: string | null
  isSubscribed: boolean
  discountApplied: boolean
  discountEndDate: string | null
  
  // Loading states
  loading: boolean
  purchasing: boolean
  cancelling: boolean
  
  // Error state
  error: string | null
  
  // Cancellation flow
  cancellationStage: CancellationStage | null
  cancellationMessage: string | null
  discountOffer: DiscountOffer | null
  subscriptionEndsAt: string | null
  
  // Last fetch time
  lastFetched: number | null
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState: SubscriptionState = {
  plan: 'none',
  status: 'none',
  billingCycle: null,
  currentPeriodEnd: null,
  isSubscribed: false,
  discountApplied: false,
  discountEndDate: null,
  
  loading: false,
  purchasing: false,
  cancelling: false,
  
  error: null,
  
  cancellationStage: null,
  cancellationMessage: null,
  discountOffer: null,
  subscriptionEndsAt: null,
  
  lastFetched: null,
}

// ============================================================================
// ASYNC THUNKS
// ============================================================================

/**
 * Fetch subscription status from the API
 */
export const fetchSubscriptionStatus = createAsyncThunk(
  'subscription/fetchStatus',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await subscriptionService.getSubscriptionStatus(userId)
      return response
    } catch (error: any) {
      console.error('Failed to fetch subscription status:', error)
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch subscription status')
    }
  }
)

/**
 * Purchase a subscription
 */
export const purchaseSubscription = createAsyncThunk(
  'subscription/purchase',
  async (
    { userId, plan, billingCycle, applyDiscount }: { 
      userId: string
      plan: SubscriptionPlan
      billingCycle: BillingCycle
      applyDiscount?: boolean 
    },
    { rejectWithValue }
  ) => {
    try {
      const response = await subscriptionService.purchaseSubscription({
        user_id: userId,
        plan,
        billing_cycle: billingCycle,
        apply_discount: applyDiscount,
      })
      return response
    } catch (error: any) {
      console.error('Failed to purchase subscription:', error)
      return rejectWithValue(error.response?.data?.detail || 'Failed to purchase subscription')
    }
  }
)

/**
 * Cancel subscription (multi-step flow)
 */
export const cancelSubscription = createAsyncThunk(
  'subscription/cancel',
  async (
    { userId, stage, reason, acceptDiscount }: {
      userId: string
      stage: CancellationStage
      reason?: string
      acceptDiscount?: boolean
    },
    { rejectWithValue }
  ) => {
    try {
      const response = await subscriptionService.cancelSubscription({
        user_id: userId,
        stage,
        reason,
        accept_discount: acceptDiscount,
      })
      return response
    } catch (error: any) {
      console.error('Failed to cancel subscription:', error)
      return rejectWithValue(error.response?.data?.detail || 'Failed to cancel subscription')
    }
  }
)

/**
 * Resubscribe (for users who cancelled)
 */
export const resubscribe = createAsyncThunk(
  'subscription/resubscribe',
  async (
    { userId, plan, billingCycle, applyDiscount }: {
      userId: string
      plan: SubscriptionPlan
      billingCycle: BillingCycle
      applyDiscount?: boolean
    },
    { rejectWithValue }
  ) => {
    try {
      const response = await subscriptionService.resubscribe({
        user_id: userId,
        plan,
        billing_cycle: billingCycle,
        apply_discount: applyDiscount,
      })
      return response
    } catch (error: any) {
      console.error('Failed to resubscribe:', error)
      return rejectWithValue(error.response?.data?.detail || 'Failed to resubscribe')
    }
  }
)

// ============================================================================
// SLICE
// ============================================================================

const subscriptionSlice = createSlice({
  name: 'subscription',
  initialState,
  reducers: {
    // Set subscription data directly (e.g., from user profile)
    setSubscription: (state, action: PayloadAction<{
      plan: SubscriptionPlan
      status: SubscriptionStatus
      billingCycle?: BillingCycle | null
      currentPeriodEnd?: string | null
      discountApplied?: boolean
    }>) => {
      state.plan = action.payload.plan
      state.status = action.payload.status
      state.billingCycle = action.payload.billingCycle || null
      state.currentPeriodEnd = action.payload.currentPeriodEnd || null
      state.discountApplied = action.payload.discountApplied || false
      state.isSubscribed = ['active', 'pending_cancellation'].includes(action.payload.status)
    },
    
    // Clear subscription state
    clearSubscription: (state) => {
      Object.assign(state, initialState)
    },
    
    // Clear error
    clearError: (state) => {
      state.error = null
    },
    
    // Reset cancellation flow
    resetCancellationFlow: (state) => {
      state.cancellationStage = null
      state.cancellationMessage = null
      state.discountOffer = null
      state.subscriptionEndsAt = null
      state.cancelling = false
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch subscription status
      .addCase(fetchSubscriptionStatus.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSubscriptionStatus.fulfilled, (state, action) => {
        state.loading = false
        state.plan = action.payload.subscription_plan
        state.status = action.payload.subscription_status
        state.billingCycle = action.payload.billing_cycle
        state.currentPeriodEnd = action.payload.current_period_end
        state.isSubscribed = action.payload.is_subscribed
        state.discountApplied = action.payload.discount_applied
        state.discountEndDate = action.payload.discount_end_date
        state.lastFetched = Date.now()
      })
      .addCase(fetchSubscriptionStatus.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      
      // Purchase subscription
      .addCase(purchaseSubscription.pending, (state) => {
        state.purchasing = true
        state.error = null
      })
      .addCase(purchaseSubscription.fulfilled, (state, action) => {
        state.purchasing = false
        if (!action.payload.already_subscribed) {
          state.plan = action.payload.plan
          state.status = 'active'
          state.billingCycle = action.payload.billing_cycle
          state.isSubscribed = true
        }
      })
      .addCase(purchaseSubscription.rejected, (state, action) => {
        state.purchasing = false
        state.error = action.payload as string
      })
      
      // Cancel subscription
      .addCase(cancelSubscription.pending, (state) => {
        state.cancelling = true
        state.error = null
      })
      .addCase(cancelSubscription.fulfilled, (state, action) => {
        state.cancelling = false
        state.cancellationStage = action.payload.stage
        state.cancellationMessage = action.payload.message
        state.discountOffer = action.payload.discount_offer
        state.subscriptionEndsAt = action.payload.subscription_ends_at
        
        // If discount was accepted, update discount status
        if (action.payload.stage === 'discount_accepted') {
          state.discountApplied = true
        }
        
        // If cancellation is complete
        if (action.payload.cancelled) {
          state.status = 'pending_cancellation'
        }
      })
      .addCase(cancelSubscription.rejected, (state, action) => {
        state.cancelling = false
        state.error = action.payload as string
      })
      
      // Resubscribe
      .addCase(resubscribe.pending, (state) => {
        state.purchasing = true
        state.error = null
      })
      .addCase(resubscribe.fulfilled, (state, action) => {
        state.purchasing = false
        state.plan = action.payload.plan
        state.status = 'active'
        state.billingCycle = action.payload.billing_cycle
        state.isSubscribed = true
        // Reset cancellation state
        state.cancellationStage = null
        state.cancellationMessage = null
        state.subscriptionEndsAt = null
      })
      .addCase(resubscribe.rejected, (state, action) => {
        state.purchasing = false
        state.error = action.payload as string
      })
  },
})

// ============================================================================
// EXPORTS
// ============================================================================

export const { 
  setSubscription, 
  clearSubscription, 
  clearError,
  resetCancellationFlow,
} = subscriptionSlice.actions

// Selectors
export const selectSubscription = (state: RootState) => state.subscription
export const selectSubscriptionPlan = (state: RootState) => state.subscription.plan
export const selectSubscriptionStatus = (state: RootState) => state.subscription.status
export const selectIsSubscribed = (state: RootState) => state.subscription.isSubscribed
export const selectSubscriptionLoading = (state: RootState) => state.subscription.loading
export const selectSubscriptionError = (state: RootState) => state.subscription.error
export const selectCancellationStage = (state: RootState) => state.subscription.cancellationStage
export const selectDiscountOffer = (state: RootState) => state.subscription.discountOffer
export const selectDiscountApplied = (state: RootState) => state.subscription.discountApplied

export default subscriptionSlice.reducer
