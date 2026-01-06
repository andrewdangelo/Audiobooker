/**
 * Cart Sidebar Component
 * 
 * A slide-out panel that displays the user's shopping cart.
 * Accessible from the navbar cart icon on all authenticated pages.
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - Slide-out animation from right side
 * - Shows all cart items with book covers
 * - Remove individual items
 * - Quantity adjustment
 * - Subtotal display
 * - Quick checkout button
 * 
 * API INTEGRATION POINTS:
 * - Cart items are synced with backend via cartSlice
 * - Book details fetched from store state
 */

import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { X, ShoppingCart, Trash2, Plus, Minus, CreditCard } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { 
  useAppDispatch, 
  useAppSelector,
} from '@/store/hooks'
import {
  selectCartItems,
  selectCartItemCount,
  selectCartTotalPrice,
  selectCartTotalCredits,
  selectIsCartEmpty,
  removeFromCart,
  updateCartQuantity,
} from '@/store/slices/cartSlice'
import { selectStoreBooks } from '@/store/slices/storeSlice'
import type { CartItem } from '@/store/slices/cartSlice'
import type { StoreBook } from '@/store/slices/storeSlice'

// ============================================================================
// TYPES
// ============================================================================

interface CartSidebarProps {
  isOpen: boolean
  onClose: () => void
}

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
    <div className="flex gap-3 py-4">
      {/* Book Cover */}
      <Link 
        to={`/store/book/${book.id}`}
        className="flex-shrink-0"
      >
        <img
          src={book.coverImage || '/placeholder-cover.jpg'}
          alt={book.title}
          className="w-16 h-24 object-cover rounded-md shadow-sm hover:shadow-md transition-shadow"
        />
      </Link>
      
      {/* Book Details */}
      <div className="flex-1 min-w-0">
        <Link 
          to={`/store/book/${book.id}`}
          className="hover:underline"
        >
          <h4 className="font-medium text-sm line-clamp-2">{book.title}</h4>
        </Link>
        <p className="text-xs text-muted-foreground mt-0.5">{book.author}</p>
        
        {/* Price */}
        <div className="mt-2 flex items-center gap-2 text-sm">
          <span className="font-semibold">{formatPrice(priceAtAdd)}</span>
          <span className="text-muted-foreground">or</span>
          <span className="text-primary font-medium">{creditsAtAdd} credit{creditsAtAdd !== 1 ? 's' : ''}</span>
        </div>
        
        {/* Quantity Controls */}
        <div className="mt-2 flex items-center gap-2">
          <div className="flex items-center border rounded-md">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-r-none"
              onClick={() => onUpdateQuantity(quantity - 1)}
              disabled={quantity <= 1}
            >
              <Minus className="h-3 w-3" />
            </Button>
            <span className="w-8 text-center text-sm font-medium">{quantity}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-l-none"
              onClick={() => onUpdateQuantity(quantity + 1)}
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>
          
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={onRemove}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function CartSidebar({ isOpen, onClose }: CartSidebarProps) {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  
  // Redux state
  const cartItems = useAppSelector(selectCartItems)
  const storeBooks = useAppSelector(selectStoreBooks)
  const itemCount = useAppSelector(selectCartItemCount)
  const totalPrice = useAppSelector(selectCartTotalPrice)
  const totalCredits = useAppSelector(selectCartTotalCredits)
  const isEmpty = useAppSelector(selectIsCartEmpty)
  
  // Join cart items with book data
  const itemsWithBooks: CartItemWithBook[] = cartItems
    .map((item: CartItem) => {
      const book = storeBooks.find((b: StoreBook) => b.id === item.bookId)
      return book ? { ...item, book } : null
    })
    .filter((item): item is CartItemWithBook => item !== null)
  
  // Close sidebar on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])
  
  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])
  
  /**
   * Handle remove item from cart
   * 
   * TODO: API INTEGRATION
   * After removing, sync cart state with backend
   */
  const handleRemove = (bookId: string) => {
    dispatch(removeFromCart(bookId))
  }
  
  /**
   * Handle quantity update
   * 
   * TODO: API INTEGRATION
   * After updating, sync cart state with backend
   */
  const handleUpdateQuantity = (bookId: string, quantity: number) => {
    if (quantity <= 0) {
      dispatch(removeFromCart(bookId))
    } else {
      dispatch(updateCartQuantity({ bookId, quantity }))
    }
  }
  
  /**
   * Navigate to checkout
   */
  const handleCheckout = () => {
    onClose()
    navigate('/checkout')
  }
  
  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/50 z-40 transition-opacity duration-300',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
      />
      
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 right-0 h-full w-full sm:w-[400px] bg-background z-50',
          'flex flex-col shadow-2xl border-l',
          'transform transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-background">
          <div className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" />
            <h2 className="font-semibold text-lg">Your Cart</h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>
        
        {/* Cart Content */}
        {isEmpty ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center bg-background">
            <ShoppingCart className="h-16 w-16 text-muted-foreground/30 mb-4" />
            <h3 className="font-medium text-lg mb-2">Your cart is empty</h3>
            <p className="text-muted-foreground text-sm mb-6">
              Discover amazing audiobooks in our store
            </p>
            <Button onClick={() => { onClose(); navigate('/store') }}>
              Browse Store
            </Button>
          </div>
        ) : (
          <>
            {/* Item count subheader */}
            <div className="px-4 py-2 bg-muted/50 border-b text-sm text-muted-foreground">
              {itemCount} item{itemCount !== 1 ? 's' : ''} in your cart
            </div>
            
            {/* Items List */}
            <ScrollArea className="flex-1 bg-background">
              <div className="divide-y p-4">
                {itemsWithBooks.map((item) => (
                  <CartItemRow
                    key={item.bookId}
                    item={item}
                    onRemove={() => handleRemove(item.bookId)}
                    onUpdateQuantity={(qty) => handleUpdateQuantity(item.bookId, qty)}
                  />
                ))}
              </div>
            </ScrollArea>
            
            {/* Footer with Totals */}
            <div className="border-t p-4 space-y-4 bg-background">
              {/* Subtotal */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span className="font-semibold">{formatPrice(totalPrice)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Or pay with credits</span>
                  <span className="font-semibold text-primary">{totalCredits} credits</span>
                </div>
              </div>
              
              <Separator />
              
              {/* Action Buttons */}
              <div className="space-y-2">
                <Button 
                  className="w-full" 
                  size="lg"
                  onClick={handleCheckout}
                >
                  <CreditCard className="h-4 w-4 mr-2" />
                  Checkout
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => { onClose(); navigate('/store') }}
                >
                  Continue Shopping
                </Button>
              </div>
            </div>
          </>
        )}
      </aside>
    </>
  )
}

export default CartSidebar
