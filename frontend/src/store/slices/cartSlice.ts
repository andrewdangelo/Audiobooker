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
import { cartApiService, storeService } from '@/services/backendService'

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
  // Edition selected at add time ('basic' = standard, 'premium' = theatrical full-cast)
  edition?: 'basic' | 'premium'
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
 * Syncs local cart state to the server so the cart persists across devices.
 * API: POST /backend/cart/sync
 */
export const syncCart = createAsyncThunk(
  'cart/sync',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const userId: string = (state as { auth?: { user?: { id?: string } } }).auth?.user?.id ?? ''
      const cartItems = state.cart.itemIds.map((id: string) => state.cart.items[id])
      const data = await cartApiService.sync(userId, cartItems)
      return {
        items: (data.items as CartItem[]) ?? cartItems,
        lastSyncedAt: (data.last_synced_at as string) ?? new Date().toISOString(),
      }
    } catch (error) {
      return rejectWithValue('Failed to sync cart')
    }
  }
)

/**
 * Validate cart items before checkout
 *
 * Verifies that all cart items are still available and prices are current.
 * API: POST /backend/cart/validate
 */
export const validateCart = createAsyncThunk(
  'cart/validate',
  async (_, { getState, rejectWithValue }) => {
    try {
      const state = getState() as RootState
      const userId: string = (state as { auth?: { user?: { id?: string } } }).auth?.user?.id ?? ''
      const data = await cartApiService.validate(userId)
      return {
        valid: (data.valid as boolean) ?? true,
        invalidItems: (data.invalid_items as string[]) ?? [],
        priceChanges: (data.price_changes as unknown[]) ?? [],
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
 * - POST /backend/store/purchase for explicit ownership fulfillment (idempotent)
 *
 * @param itemsOverride  When provided, these items are used instead of the cart.
 *                       Use for direct / single-book purchases that must not
 *                       pollute the persisted cart.
 * @param clearCartOnSuccess  When false the Redux cart is NOT cleared after a
 *                            successful checkout (default: true).
 */
export const checkout = createAsyncThunk(
  'cart/checkout',
  async (
    {
      paymentMethod,
      paymentId,
      itemsOverride,
      clearCartOnSuccess = true,
    }: {
      paymentMethod: 'credits' | 'card'
      paymentId?: string | null
      itemsOverride?: Array<{ bookId: string; quantity: number; priceAtAdd: number; creditsAtAdd: number }>
      clearCartOnSuccess?: boolean
    },
    { getState, rejectWithValue }
  ) => {
    try {
      const state = getState() as RootState
      const cartItems = state.cart.itemIds.map((id: string) => state.cart.items[id])
      const effectiveItems = itemsOverride ?? cartItems
      const userId = state.auth?.user?.id

      if (!userId) {
        throw new Error('User not authenticated')
      }

      const paymentItems = effectiveItems.map((item) => ({
        book_id: item.bookId,
        quantity: item.quantity,
        price_cents: item.priceAtAdd,
        credits: item.creditsAtAdd,
        title: state.store.books[item.bookId]?.title || `Book ${item.bookId}`,
      }))

      if (paymentMethod === 'credits') {
        // Process credits payment via payment service
        const response = await paymentService.payWithCredits({
          user_id: userId,
          items: paymentItems,
          currency: 'usd',
          metadata: {
            item_count: String(effectiveItems.length),
            book_ids: effectiveItems.map((item) => item.bookId).join(','),
          },
        })

        return {
          success: true,
          orderId: response.order_id,
          purchasedBooks: effectiveItems.map((item) => item.bookId),
          remainingCredits: response.remaining_credits,
          clearCartOnSuccess,
        }
      } else {
        // Card payment - the payment intent was already confirmed via Stripe Elements.
        // Stripe's SDK only calls onSuccess after client-side confirmation is complete,
        // so we trust that confirmation directly. Do NOT re-check our own DB payment record
        // status here: the Stripe webhook that flips it to "succeeded" is asynchronous and
        // almost always arrives AFTER this code runs, causing a false "pending" error that
        // blocked the checkout from advancing.
        if (!paymentId) {
          throw new Error('Missing payment record')
        }

        // Explicitly fulfill ownership for every purchased item (idempotent backend endpoint).
        // The webhook is a secondary safety net; this guarantees ownership is visible immediately.
        for (const item of effectiveItems) {
          try {
            await storeService.purchase(userId, item.bookId, 'card')
          } catch {
            // Best-effort: a backend webhook will catch any gap
          }
        }

        return {
          success: true,
          orderId: paymentId,
          purchasedBooks: effectiveItems.map((item) => item.bookId),
          remainingCredits: state.store.userCredits,
          clearCartOnSuccess,
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
        edition?: 'basic' | 'premium'
      }>
    ) => {
      const { bookId, price, credits, quantity = 1, edition } = action.payload
      
      if (state.items[bookId]) {
        // Item exists — update quantity and refresh edition/price in case
        // the user switched editions before re-adding.
        state.items[bookId].quantity += quantity
        if (edition) state.items[bookId].edition = edition
        state.items[bookId].priceAtAdd = price
        state.items[bookId].creditsAtAdd = credits
      } else {
        // New item - add to cart
        state.items[bookId] = {
          bookId,
          quantity,
          addedAt: new Date().toISOString(),
          priceAtAdd: price,
          creditsAtAdd: credits,
          edition,
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
      .addCase(checkout.fulfilled, (state, action) => {
        state.isCheckingOut = false
        state.checkoutStep = 'success'
        // Only clear the cart for normal cart-based checkouts;
        // direct single-book purchases leave the cart intact.
        if (action.payload.clearCartOnSuccess !== false) {
          state.items = {}
          state.itemIds = []
        }
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
