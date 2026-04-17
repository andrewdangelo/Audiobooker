/**
 * Payment Service
 * 
 * Handles all payment-related API calls to the payment microservice
 * through the API proxy.
 * 
 * @author Andrew D'Angelo
 */

import api from './api'

// ============================================================================
// TYPES
// ============================================================================

export interface PaymentCartItem {
  book_id: string
  quantity: number
  price_cents: number
  credits: number
  title: string
}

export interface PaymentIntentRequest {
  user_id: string
  items?: PaymentCartItem[]
  amount?: number  // in cents
  currency?: string
  metadata?: Record<string, string>
}

export interface PaymentIntentResponse {
  payment_id: string
  client_secret: string
  payment_intent_id: string
  amount_cents: number
  currency: string
  status: string
}

export interface CheckoutSessionRequest {
  user_id: string
  items: PaymentCartItem[]
  customer_email?: string
  success_url?: string
  cancel_url?: string
}

export interface CheckoutSessionResponse {
  session_id: string
  checkout_url: string
  payment_id: string
  amount_cents: number
  currency: string
}

export interface CreditsPaymentRequest {
  user_id: string
  items?: PaymentCartItem[]
  amount?: number  // in cents equivalent
  currency?: string
  metadata?: Record<string, string>
}

export interface CreditsPaymentResponse {
  payment_id: string
  order_id: string
  credits_deducted: number
  remaining_credits: number
  status: string
  message: string
}

export interface PaymentStatusResponse {
  payment_id: string
  stripe_payment_intent_id?: string | null
  status: string
  amount_cents: number
  currency: string
  payment_method: string
  metadata?: Record<string, string> | null
  created_at: string
  updated_at?: string | null
}

export interface PublishableKeyResponse {
  publishable_key: string
  mode: 'test' | 'live'
}

export interface UserPaymentsResponse {
  payments: PaymentStatusResponse[]
  count: number
}

export interface UserOrdersResponse {
  orders: OrderResponse[]
  count: number
}

export interface OrderResponse {
  order_id: string
  user_id: string
  payment_id: string
  items: PaymentCartItem[]
  total_cents: number
  total_credits: number
  status: string
  payment_method: string
  created_at: string
}

export interface SubscriptionCatalogItem {
  id: 'basic' | 'premium' | 'publisher'
  name: string
  description: string
  included_credit_type: 'basic' | 'premium'
  included_credits: number
  monthly_amount_cents: number
  annual_amount_cents: number
  features: string[]
}

export interface CreditPackResponse {
  id: string
  name: string
  description: string
  credit_type: 'basic' | 'premium'
  credits: number
  amount_cents: number
}

// ============================================================================
// API ENDPOINTS
// ============================================================================

const PAYMENT_BASE = '/payment'

/**
 * Payment Service API
 */
export const paymentService = {
  /**
   * Get Stripe publishable key for frontend initialization
   * This is called once when the app loads to initialize Stripe.js
   */
  async getPublishableKey(): Promise<PublishableKeyResponse> {
    const response = await api.get<PublishableKeyResponse>(
      `${PAYMENT_BASE}/config/publishable-key`
    )
    return response.data
  },

  /**
   * Create a payment intent for custom payment forms (Stripe Elements)
   * 
   * Use this when you want a custom payment form embedded in your page.
   * Returns a client_secret to use with Stripe.js confirmPayment().
   */
  async createPaymentIntent(request: PaymentIntentRequest): Promise<PaymentIntentResponse> {
    const response = await api.post<PaymentIntentResponse>(
      `${PAYMENT_BASE}/create-payment-intent`,
      {
        user_id: request.user_id,
        items: request.items,
        amount: request.amount,
        currency: request.currency || 'usd',
        payment_method: 'card',
        metadata: request.metadata,
      }
    )
    return response.data
  },

  /**
   * Synchronously grant credits after a Stripe payment intent succeeds.
   * Call this immediately after Stripe.js confirms the payment so that
   * the DB is updated before the success page fetches the user profile.
   * Idempotent — safe to call multiple times for the same payment intent.
   */
  async completeCreditPurchase(paymentIntentId: string): Promise<{ status: string; credits_added: number; credit_type: string }> {
    const response = await api.post(`${PAYMENT_BASE}/complete-credit-purchase`, {
      payment_intent_id: paymentIntentId,
    })
    return response.data
  },

  /**
   * Create a checkout session for Stripe hosted checkout
   * 
   * Use this when you want to redirect users to Stripe's hosted checkout page.
   * Simpler but less customizable than Payment Intents.
   */
  async createCheckoutSession(request: CheckoutSessionRequest): Promise<CheckoutSessionResponse> {
    const response = await api.post<CheckoutSessionResponse>(
      `${PAYMENT_BASE}/create-checkout-session`,
      request
    )
    return response.data
  },

  /**
   * Process payment using user credits
   * 
   * This bypasses Stripe and deducts credits directly from the user's account.
   */
  async payWithCredits(request: CreditsPaymentRequest): Promise<CreditsPaymentResponse> {
    const response = await api.post<CreditsPaymentResponse>(
      `${PAYMENT_BASE}/pay-with-credits`,
      {
        user_id: request.user_id,
        items: request.items,
        amount: request.amount,
        currency: request.currency || 'usd',
        metadata: request.metadata,
      }
    )
    return response.data
  },

  /**
   * Get payment status by payment ID
   */
  async getPaymentStatus(paymentId: string): Promise<PaymentStatusResponse> {
    const response = await api.get<PaymentStatusResponse>(
      `${PAYMENT_BASE}/payment/${paymentId}`
    )
    return response.data
  },

  /**
   * Get user's payment history
   */
  async getUserPayments(userId: string, limit = 50): Promise<UserPaymentsResponse> {
    const response = await api.get<UserPaymentsResponse>(
      `${PAYMENT_BASE}/user/${userId}/payments`,
      { params: { limit } }
    )
    return response.data
  },

  /**
   * Get user's order history
   */
  async getUserOrders(userId: string, limit = 50): Promise<UserOrdersResponse> {
    const response = await api.get<UserOrdersResponse>(
      `${PAYMENT_BASE}/user/${userId}/orders`,
      { params: { limit } }
    )
    return response.data
  },

  /**
   * Confirm payment after checkout session
   * Call this on the success page to verify payment went through
   */
  async verifyCheckoutSession(sessionId: string): Promise<{
    session_id: string
    payment_status: string
    status: string
    amount_total: number
    currency: string
  }> {
    const response = await api.get(`${PAYMENT_BASE}/checkout-session/${sessionId}`)
    return response.data
  },

  async getSubscriptionPlans(): Promise<SubscriptionCatalogItem[]> {
    const response = await api.get<SubscriptionCatalogItem[]>(
      `${PAYMENT_BASE}/subscription/pricing/plans`
    )
    return response.data
  },

  async getCreditPacks(creditType?: 'basic' | 'premium'): Promise<CreditPackResponse[]> {
    const response = await api.get<CreditPackResponse[]>(
      `${PAYMENT_BASE}/subscription/pricing/credit-packs`,
      {
        params: creditType ? { credit_type: creditType } : undefined,
      }
    )
    return response.data
  },

  async getCreditPack(packId: string): Promise<CreditPackResponse> {
    const response = await api.get<CreditPackResponse>(
      `${PAYMENT_BASE}/subscription/pricing/credit-packs/${packId}`
    )
    return response.data
  },
}

export default paymentService
