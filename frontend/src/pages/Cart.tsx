/**
 * Cart Page
 * 
 * Dedicated page for viewing and managing shopping cart items.
 * Provides full-page cart experience with item management.
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - View all cart items with book covers
 * - Adjust quantity for each item
 * - Remove individual items
 * - Price and credits subtotals
 * - Proceed to checkout button
 * - Continue shopping link
 * 
 * API INTEGRATION POINTS:
 * - Cart items are synced with backend via cartSlice
 * - Book details fetched from store state
 */

import { Link, useNavigate } from 'react-router-dom'
import {
  ShoppingCart,
  Trash2,
  Plus,
  Minus,
  ArrowLeft,
  CreditCard,
  BookOpen,
  ShoppingBag,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import {
  selectCartItems,
  selectCartItemCount,
  selectCartTotalPrice,
  selectCartTotalCredits,
  selectIsCartEmpty,
  removeFromCart,
  updateCartQuantity,
  clearCart,
} from '@/store/slices/cartSlice'
import { selectStoreBooks, selectUserCredits } from '@/store/slices/storeSlice'
import type { CartItem } from '@/store/slices/cartSlice'
import type { StoreBook } from '@/store/slices/storeSlice'

// ============================================================================
// TYPES
// ============================================================================

interface CartItemWithBook extends CartItem {
  book: StoreBook
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Format price from cents to display string
 */
function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

interface CartItemRowProps {
  item: CartItemWithBook
  onRemove: () => void
  onUpdateQuantity: (quantity: number) => void
}

function CartItemRow({ item, onRemove, onUpdateQuantity }: CartItemRowProps) {
  const { book, quantity, priceAtAdd, creditsAtAdd } = item

  return (
    <div className="flex gap-4 py-6 border-b last:border-b-0">
      {/* Book Cover */}
      <Link to={`/store/book/${book.id}`} className="flex-shrink-0">
        <img
          src={book.coverImage || '/placeholder-cover.jpg'}
          alt={book.title}
          className="w-24 h-36 object-cover rounded-lg shadow-md hover:shadow-lg transition-shadow"
        />
      </Link>

      {/* Book Details */}
      <div className="flex-1 min-w-0">
        <Link to={`/store/book/${book.id}`} className="hover:underline">
          <h3 className="font-semibold text-lg line-clamp-2">{book.title}</h3>
        </Link>
        <p className="text-muted-foreground mt-1">{book.author}</p>

        {/* Duration/Format Info */}
        {book.duration && (
          <p className="text-sm text-muted-foreground mt-2">
            Duration: {Math.floor(book.duration / 60)}h {book.duration % 60}m
          </p>
        )}

        {/* Price Display */}
        <div className="mt-3 flex items-center gap-3">
          <span className="text-lg font-bold">{formatPrice(priceAtAdd)}</span>
          <span className="text-muted-foreground">or</span>
          <span className="text-primary font-semibold">
            {creditsAtAdd} credit{creditsAtAdd !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Quantity Controls */}
        <div className="mt-4 flex items-center gap-4">
          <div className="flex items-center border rounded-lg">
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-r-none"
              onClick={() => onUpdateQuantity(quantity - 1)}
              disabled={quantity <= 1}
            >
              <Minus className="h-4 w-4" />
            </Button>
            <span className="w-12 text-center font-medium">{quantity}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-l-none"
              onClick={() => onUpdateQuantity(quantity + 1)}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={onRemove}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Remove
          </Button>
        </div>
      </div>

      {/* Item Subtotal */}
      <div className="text-right">
        <p className="text-sm text-muted-foreground">Subtotal</p>
        <p className="text-lg font-bold">{formatPrice(priceAtAdd * quantity)}</p>
        <p className="text-sm text-primary">
          {creditsAtAdd * quantity} credit{creditsAtAdd * quantity !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  )
}

function EmptyCart() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="h-24 w-24 rounded-full bg-muted flex items-center justify-center mb-6">
        <ShoppingCart className="h-12 w-12 text-muted-foreground" />
      </div>
      <h2 className="text-2xl font-semibold mb-2">Your cart is empty</h2>
      <p className="text-muted-foreground mb-6 text-center max-w-md">
        Looks like you haven't added any audiobooks to your cart yet. 
        Browse our store to discover your next great listen!
      </p>
      <Button asChild size="lg">
        <Link to="/store">
          <ShoppingBag className="h-5 w-5 mr-2" />
          Browse Store
        </Link>
      </Button>
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function Cart() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  // Redux state
  const cartItems = useAppSelector(selectCartItems)
  const storeBooks = useAppSelector(selectStoreBooks)
  const itemCount = useAppSelector(selectCartItemCount)
  const totalPrice = useAppSelector(selectCartTotalPrice)
  const totalCredits = useAppSelector(selectCartTotalCredits)
  const isEmpty = useAppSelector(selectIsCartEmpty)
  const userCredits = useAppSelector(selectUserCredits)

  // Join cart items with book data
  const itemsWithBooks: CartItemWithBook[] = cartItems
    .map((item: CartItem) => {
      const book = storeBooks.find((b: StoreBook) => b.id === item.bookId)
      return book ? { ...item, book } : null
    })
    .filter((item): item is CartItemWithBook => item !== null)

  /**
   * Handle remove item from cart
   * TODO: API INTEGRATION - Sync cart removal with backend
   */
  const handleRemoveItem = (bookId: string) => {
    dispatch(removeFromCart(bookId))
  }

  /**
   * Handle quantity update
   * TODO: API INTEGRATION - Sync quantity changes with backend
   */
  const handleUpdateQuantity = (bookId: string, quantity: number) => {
    if (quantity < 1) return
    dispatch(updateCartQuantity({ bookId, quantity }))
  }

  /**
   * Handle clear cart
   * TODO: API INTEGRATION - Sync cart clear with backend
   */
  const handleClearCart = () => {
    dispatch(clearCart())
  }

  /**
   * Navigate to checkout
   */
  const handleCheckout = () => {
    navigate('/checkout')
  }

  // Can user pay with credits?
  const canPayWithCredits = userCredits >= totalCredits

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-2">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/store">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Continue Shopping
            </Link>
          </Button>
        </div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <ShoppingCart className="h-8 w-8" />
          Shopping Cart
        </h1>
        {!isEmpty && (
          <p className="text-muted-foreground mt-1">
            {itemCount} item{itemCount !== 1 ? 's' : ''} in your cart
          </p>
        )}
      </div>

      {isEmpty ? (
        <EmptyCart />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Cart Items</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={handleClearCart}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear Cart
                </Button>
              </CardHeader>
              <CardContent>
                {itemsWithBooks.map((item) => (
                  <CartItemRow
                    key={item.bookId}
                    item={item}
                    onRemove={() => handleRemoveItem(item.bookId)}
                    onUpdateQuantity={(qty) => handleUpdateQuantity(item.bookId, qty)}
                  />
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <Card className="sticky top-24">
              <CardHeader>
                <CardTitle>Order Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Item Count */}
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Items ({itemCount})</span>
                  <span>{formatPrice(totalPrice)}</span>
                </div>

                <Separator />

                {/* Total */}
                <div className="flex justify-between font-semibold text-lg">
                  <span>Total</span>
                  <span>{formatPrice(totalPrice)}</span>
                </div>

                {/* Credits Option */}
                <div className="rounded-lg bg-muted/50 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <BookOpen className="h-4 w-4 text-primary" />
                    Pay with Credits
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Credits needed</span>
                    <span className="font-medium">{totalCredits}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Your balance</span>
                    <span className={canPayWithCredits ? 'text-green-600 font-medium' : 'text-destructive font-medium'}>
                      {userCredits} credits
                    </span>
                  </div>
                  {!canPayWithCredits && (
                    <p className="text-xs text-muted-foreground">
                      You need {totalCredits - userCredits} more credits to pay with credits only.
                    </p>
                  )}
                </div>
              </CardContent>
              <CardFooter className="flex flex-col gap-3">
                <Button className="w-full" size="lg" onClick={handleCheckout}>
                  <CreditCard className="h-5 w-5 mr-2" />
                  Proceed to Checkout
                </Button>
                <Button variant="outline" className="w-full" asChild>
                  <Link to="/store">Continue Shopping</Link>
                </Button>
              </CardFooter>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
