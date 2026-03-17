/**
 * Cart Slice
 * 
 * Manages the shopping cart state for the audiobook store including:
 * - Cart items (books to purchase)
 * - Quantities and pricing
 * - Cart totals calculation
 * - Checkout flow state
 * 
 * @author Andrew D'Angelo
 * 
 * HOW TO USE:
 * - Import actions: import { addToCart, removeFromCart, updateCartQuantity } from '@/store'
 * - Import selectors: import { selectCartItems, selectCartTotal } from '@/store'
 * 
 * PAYMENT INTEGRATION:
 * - Card payments are processed via Stripe Payment Intents
 * - Credits payments are processed via the payment microservice
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../index'
import { paymentService } from '@/services/paymentService'

// ============================================================================
// TYPES
// ============================================================================

/**
 * Cart item - represents a book added to the cart
 */
export interface CartItem {
  bookId: string
  quantity: number
  addedAt: string // ISO timestamp
  // Price at time of adding (for price lock guarantee)
  priceAtAdd: number
  creditsAtAdd: number
}

/**
 * Cart state shape
 */
export interface CartState {
  // Cart items indexed by bookId for O(1) lookup
  items: Record<string, CartItem>
  // Ordered list of item IDs (maintains add order)
  itemIds: string[]
  // Checkout flow state
  checkoutStep: 'cart' | 'payment' | 'confirm' | 'success'
  // Loading states
  isLoading: boolean
  isCheckingOut: boolean
  // Error handling
  error: string | null
  // Last sync timestamp
  lastSyncedAt: string | null
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState: CartState = {
  items: {},
  itemIds: [],
  checkoutStep: 'cart',
  isLoading: false,
  isCheckingOut: false,
  error: null,
  lastSyncedAt: null,
}

// ============================================================================
// ASYNC THUNKS
// ============================================================================

/**
 * Sync cart with backend
 * 
 * TODO: API INTEGRATION
 * This thunk should sync the local cart state with the backend.
 * This enables cart persistence across devices and sessions.
 * 
 * API Endpoint: POST /api/v1/cart/sync
 * Request Body: { items: CartItem[] }
 * Response: { items: CartItem[], lastSyncedAt: string }
 */
export const syncCart = createAsyncThunk(
  'cart/sync',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const cartItems = state.cart.itemIds.map((id: string) => state.cart.items[id])
      
      // TODO: API INTEGRATION
      // Replace with actual API call:
      // const response = await fetch(`${API_BASE_URL}/cart/sync`, {
      //   method: 'POST',
      //   headers: { 
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${state.auth.token}`
      //   },
      //   body: JSON.stringify({ items: cartItems })
      // })
      // if (!response.ok) throw new Error('Failed to sync cart')
      // return await response.json()
      
      // Mock response - just return current state
      await new Promise(resolve => setTimeout(resolve, 300))
      return {
        items: cartItems,
        lastSyncedAt: new Date().toISOString(),
      }
    } catch (error) {
      return rejectWithValue('Failed to sync cart')
    }
  }
)

/**
 * Validate cart items before checkout
 * 
 * TODO: API INTEGRATION
 * This thunk should validate that all cart items are still available
 * and that prices haven't changed significantly.
 * 
 * API Endpoint: POST /api/v1/cart/validate
 * Request Body: { items: CartItem[] }
 * Response: { valid: boolean, invalidItems: string[], priceChanges: PriceChange[] }
 */
export const validateCart = createAsyncThunk(
  'cart/validate',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      // Cart items would be sent to API for validation
      // const cartItems = state.cart.itemIds.map((id: string) => state.cart.items[id])
      void state // Mark as used for now
      
      // TODO: API INTEGRATION
      // Replace with actual API call:
      // const response = await fetch(`${API_BASE_URL}/cart/validate`, {
      //   method: 'POST',
      //   headers: { 
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${state.auth.token}`
      //   },
      //   body: JSON.stringify({ items: cartItems })
      // })
      // if (!response.ok) throw new Error('Failed to validate cart')
      // return await response.json()
      
      // Mock response - all items valid
      await new Promise(resolve => setTimeout(resolve, 500))
      return {
        valid: true,
        invalidItems: [],
        priceChanges: [],
      }
    } catch (error) {
      return rejectWithValue('Failed to validate cart')
    }
  }
)

/**
 * Process checkout and complete purchase
 * 
 * This thunk processes the final purchase:
 * - For card payments: The payment intent was already confirmed via Stripe Elements
 * - For credits payments: Calls the payment service to deduct credits
 * 
 * API Endpoints:
 * - POST /payment/pay-with-credits (for credits payment)
 * - Payment Intent status check for card payments
 */
export const checkout = createAsyncThunk(
  'cart/checkout',
  async (
    { paymentMethod, paymentIntentId }: { paymentMethod: 'credits' | 'card'; paymentIntentId?: string | null },
    { getState, rejectWithValue }
  ) => {
    try {
      const state = getState() as RootState
      const cartItems = state.cart.itemIds.map((id: string) => state.cart.items[id])
      const totalCredits = cartItems.reduce((sum: number, item: CartItem) => sum + item.creditsAtAdd * item.quantity, 0)
      const totalPrice = cartItems.reduce((sum: number, item: CartItem) => sum + item.priceAtAdd * item.quantity, 0)
      const userId = state.auth?.user?.id

      if (!userId) {
        throw new Error('User not authenticated')
      }

      if (paymentMethod === 'credits') {
        // Process credits payment via payment service
        const response = await paymentService.payWithCredits({
          user_id: userId,
          amount: totalPrice,
          currency: 'usd',
          metadata: {
            item_count: String(cartItems.length),
            book_ids: cartItems.map((item: CartItem) => item.bookId).join(','),
          },
        })

        return {
          success: true,
          orderId: response.order_id,
          purchasedBooks: cartItems.map((item: CartItem) => item.bookId),
          remainingCredits: response.remaining_credits,
        }
      } else {
        // Card payment - the payment intent was already confirmed via Stripe Elements
        // Just verify the payment was successful if we have a payment intent ID
        if (paymentIntentId) {
          const paymentStatus = await paymentService.getPaymentStatus(paymentIntentId)
          if (paymentStatus.status !== 'succeeded') {
            throw new Error(`Payment not completed: ${paymentStatus.status}`)
          }
        }

        return {
          success: true,
          orderId: paymentIntentId || `ORD-${Date.now()}`,
          purchasedBooks: cartItems.map((item: CartItem) => item.bookId),
          remainingCredits: state.store.userCredits,
        }
      }
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Checkout failed')
    }
  }
)

// ============================================================================
// SLICE
// ============================================================================

const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    /**
     * Add item to cart
     * If item already exists, increment quantity
     */
    addToCart: (
      state,
      action: PayloadAction<{
        bookId: string
        price: number
        credits: number
        quantity?: number
      }>
    ) => {
      const { bookId, price, credits, quantity = 1 } = action.payload
      
      if (state.items[bookId]) {
        // Item exists - increment quantity
        state.items[bookId].quantity += quantity
      } else {
        // New item - add to cart
        state.items[bookId] = {
          bookId,
          quantity,
          addedAt: new Date().toISOString(),
          priceAtAdd: price,
          creditsAtAdd: credits,
        }
        state.itemIds.push(bookId)
      }
      
      // Clear any previous errors
      state.error = null
    },
    
    /**
     * Remove item from cart
     */
    removeFromCart: (state, action: PayloadAction<string>) => {
      const bookId = action.payload
      
      if (state.items[bookId]) {
        delete state.items[bookId]
        state.itemIds = state.itemIds.filter(id => id !== bookId)
      }
    },
    
    /**
     * Update item quantity
     */
    updateCartQuantity: (
      state,
      action: PayloadAction<{ bookId: string; quantity: number }>
    ) => {
      const { bookId, quantity } = action.payload
      
      if (state.items[bookId]) {
        if (quantity <= 0) {
          // Remove if quantity is 0 or negative
          delete state.items[bookId]
          state.itemIds = state.itemIds.filter(id => id !== bookId)
        } else {
          state.items[bookId].quantity = quantity
        }
      }
    },
    
    /**
     * Clear entire cart
     */
    clearCart: (state) => {
      state.items = {}
      state.itemIds = []
      state.error = null
    },
    
    /**
     * Set checkout step
     */
    setCheckoutStep: (
      state,
      action: PayloadAction<'cart' | 'payment' | 'confirm' | 'success'>
    ) => {
      state.checkoutStep = action.payload
    },
    
    /**
     * Reset checkout flow
     */
    resetCheckout: (state) => {
      state.checkoutStep = 'cart'
      state.isCheckingOut = false
      state.error = null
    },
    
    /**
     * Clear cart error
     */
    clearCartError: (state) => {
      state.error = null
    },
  },
  
  extraReducers: (builder) => {
    builder
      // Sync cart
      .addCase(syncCart.pending, (state) => {
        state.isLoading = true
      })
      .addCase(syncCart.fulfilled, (state, action) => {
        state.isLoading = false
        state.lastSyncedAt = action.payload.lastSyncedAt
      })
      .addCase(syncCart.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as string
      })
      
      // Validate cart
      .addCase(validateCart.pending, (state) => {
        state.isLoading = true
      })
      .addCase(validateCart.fulfilled, (state) => {
        state.isLoading = false
      })
      .addCase(validateCart.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as string
      })
      
      // Checkout
      .addCase(checkout.pending, (state) => {
        state.isCheckingOut = true
        state.error = null
      })
      .addCase(checkout.fulfilled, (state) => {
        state.isCheckingOut = false
        state.checkoutStep = 'success'
        // Clear cart after successful checkout
        state.items = {}
        state.itemIds = []
      })
      .addCase(checkout.rejected, (state, action) => {
        state.isCheckingOut = false
        state.error = action.payload as string
      })
  },
})

// ============================================================================
// ACTIONS
// ============================================================================

export const {
  addToCart,
  removeFromCart,
  updateCartQuantity,
  clearCart,
  setCheckoutStep,
  resetCheckout,
  clearCartError,
} = cartSlice.actions

// ============================================================================
// SELECTORS
// ============================================================================

/**
 * Select all cart items
 */
export const selectCartItems = (state: RootState): CartItem[] =>
  state.cart.itemIds.map((id: string) => state.cart.items[id])

/**
 * Select cart item by book ID
 */
export const selectCartItemById = (state: RootState, bookId: string): CartItem | undefined =>
  state.cart.items[bookId]

/**
 * Select total number of items in cart
 */
export const selectCartItemCount = (state: RootState): number =>
  state.cart.itemIds.reduce((count: number, id: string) => count + (state.cart.items[id]?.quantity || 0), 0)

/**
 * Select cart total price (in cents)
 */
export const selectCartTotalPrice = (state: RootState): number =>
  state.cart.itemIds.reduce((total: number, id: string) => {
    const item = state.cart.items[id]
    return total + (item ? item.priceAtAdd * item.quantity : 0)
  }, 0)

/**
 * Select cart total credits
 */
export const selectCartTotalCredits = (state: RootState): number =>
  state.cart.itemIds.reduce((total: number, id: string) => {
    const item = state.cart.items[id]
    return total + (item ? item.creditsAtAdd * item.quantity : 0)
  }, 0)

/**
 * Check if a book is in cart
 */
export const selectIsInCart = (state: RootState, bookId: string): boolean =>
  bookId in state.cart.items

/**
 * Select checkout step
 */
export const selectCheckoutStep = (state: RootState) => state.cart.checkoutStep

/**
 * Select cart loading state
 */
export const selectCartLoading = (state: RootState): boolean => state.cart.isLoading

/**
 * Select checkout in progress
 */
export const selectIsCheckingOut = (state: RootState): boolean => state.cart.isCheckingOut

/**
 * Select cart error
 */
export const selectCartError = (state: RootState): string | null => state.cart.error

/**
 * Select if cart is empty
 */
export const selectIsCartEmpty = (state: RootState): boolean => state.cart.itemIds.length === 0

export default cartSlice.reducer
