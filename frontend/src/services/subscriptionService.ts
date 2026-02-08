/**
 * Subscription Service
 * 
 * Handles all subscription-related API calls to the payment microservice
 * through the API proxy.
 * 
 * @author Audiobooker Team
 */

import api from './api'

// ============================================================================
// TYPES
// ============================================================================

export type SubscriptionPlan = 'none' | 'basic' | 'premium'
export type SubscriptionStatus = 'none' | 'active' | 'cancelled' | 'expired' | 'pending_cancellation'
export type BillingCycle = 'monthly' | 'annual'
export type CancellationStage = 'initial' | 'reason_collected' | 'discount_offered' | 'discount_accepted' | 'final_confirmation' | 'cancelled'

export interface SubscriptionStatusResponse {
  user_id: string
  subscription_plan: SubscriptionPlan
  subscription_status: SubscriptionStatus
  billing_cycle: BillingCycle | null
  current_period_end: string | null
  is_subscribed: boolean
  discount_applied: boolean
  discount_end_date: string | null
}

export interface SubscriptionPurchaseRequest {
  user_id: string
  plan: SubscriptionPlan
  billing_cycle?: BillingCycle
  customer_email?: string
  success_url?: string
  cancel_url?: string
  apply_discount?: boolean
}

export interface SubscriptionPurchaseResponse {
  subscription_id: string
  checkout_url: string | null
  client_secret: string | null
  plan: SubscriptionPlan
  billing_cycle: BillingCycle
  amount_cents: number
  status: string
  already_subscribed: boolean
  message: string
}

export interface CancellationRequest {
  user_id: string
  reason?: string
  stage: CancellationStage
  accept_discount?: boolean
}

export interface DiscountOffer {
  type: string
  discount_percentage: number
  duration_months: number
  original_price_cents: number
  discounted_price_cents: number
  original_price_display: string
  discounted_price_display: string
  savings_display: string
  message: string
}

export interface CancellationResponse {
  user_id: string
  stage: CancellationStage
  message: string
  discount_offer: DiscountOffer | null
  subscription_ends_at: string | null
  cancelled: boolean
}

export interface RetentionOffer {
  offer_type: string
  discount_percentage: number
  duration_months: number
  original_price_cents: number
  discounted_price_cents: number
  message: string
}

// ============================================================================
// SUBSCRIPTION PRICES (for display purposes)
// ============================================================================

export const SUBSCRIPTION_PRICES = {
  basic: {
    monthly: 999,    // $9.99
    annual: 9999,    // $99.99
  },
  premium: {
    monthly: 1999,   // $19.99
    annual: 19999,   // $199.99
  }
}

export const formatPrice = (cents: number): string => {
  return `$${(cents / 100).toFixed(2)}`
}

// ============================================================================
// API ENDPOINTS
// ============================================================================

const PAYMENT_BASE = '/payment'

/**
 * Subscription Service API
 */
export const subscriptionService = {
  /**
   * Get user's current subscription status
   */
  async getSubscriptionStatus(userId: string): Promise<SubscriptionStatusResponse> {
    const response = await api.get<SubscriptionStatusResponse>(
      `${PAYMENT_BASE}/subscription/status/${userId}`
    )
    return response.data
  },

  /**
   * Purchase a subscription plan
   * 
   * Includes guard - will return already_subscribed: true if user is already subscribed
   */
  async purchaseSubscription(request: SubscriptionPurchaseRequest): Promise<SubscriptionPurchaseResponse> {
    const response = await api.post<SubscriptionPurchaseResponse>(
      `${PAYMENT_BASE}/subscription/purchase`,
      {
        user_id: request.user_id,
        plan: request.plan,
        billing_cycle: request.billing_cycle || 'monthly',
        customer_email: request.customer_email,
        success_url: request.success_url,
        cancel_url: request.cancel_url,
        apply_discount: request.apply_discount || false,
      }
    )
    return response.data
  },

  /**
   * Cancel subscription with retention flow
   * 
   * This is a multi-step process:
   * 1. Initial - shows "are you sure?"
   * 2. Reason collected - offers discount
   * 3. Discount offered - can accept or decline
   * 4. Final confirmation - last chance
   * 5. Cancelled - subscription set to cancel at period end
   */
  async cancelSubscription(request: CancellationRequest): Promise<CancellationResponse> {
    const response = await api.post<CancellationResponse>(
      `${PAYMENT_BASE}/subscription/cancel`,
      {
        user_id: request.user_id,
        reason: request.reason,
        stage: request.stage,
        accept_discount: request.accept_discount || false,
      }
    )
    return response.data
  },

  /**
   * Resubscribe - for users who cancelled or have pending cancellation
   */
  async resubscribe(request: SubscriptionPurchaseRequest): Promise<SubscriptionPurchaseResponse> {
    const response = await api.post<SubscriptionPurchaseResponse>(
      `${PAYMENT_BASE}/subscription/resubscribe`,
      {
        user_id: request.user_id,
        plan: request.plan,
        billing_cycle: request.billing_cycle || 'monthly',
        apply_discount: request.apply_discount || false,
      }
    )
    return response.data
  },

  /**
   * Get retention offer for a user
   */
  async getRetentionOffer(userId: string): Promise<RetentionOffer> {
    const response = await api.get<RetentionOffer>(
      `${PAYMENT_BASE}/subscription/retention-offer/${userId}`
    )
    return response.data
  },
}

export default subscriptionService
