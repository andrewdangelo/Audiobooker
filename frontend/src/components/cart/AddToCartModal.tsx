/**
 * Add to Cart Modal Component
 * 
 * Confirmation modal displayed when a user clicks the "Buy" button.
 * Shows book details, allows quantity selection, and provides options
 * to continue shopping or proceed to checkout.
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - Book cover and details display
 * - Quantity selector
 * - Price and credits display
 * - Add to cart or continue shopping options
 * 
 * API INTEGRATION POINTS:
 * - Item is added to cart via cartSlice
 * - Cart synced with backend after addition
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShoppingCart, Check, Plus, Minus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { addToCart, selectIsInCart } from '@/store/slices/cartSlice'
import type { StoreBook } from '@/store/slices/storeSlice'

// ============================================================================
// TYPES
// ============================================================================

interface AddToCartModalProps {
  book: StoreBook | null
  isOpen: boolean
  onClose: () => void
  onOpenCart?: () => void
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
// MAIN COMPONENT
// ============================================================================

export function AddToCartModal({ book, isOpen, onClose, onOpenCart }: AddToCartModalProps) {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  
  const [quantity, setQuantity] = useState(1)
  const [isAdded, setIsAdded] = useState(false)
  
  // Check if item is already in cart
  const isInCart = useAppSelector((state) => 
    book ? selectIsInCart(state, book.id) : false
  )
  
  // Reset state when modal opens/closes
  const handleOpenChange = (open: boolean) => {
    if (!open) {
      onClose()
      // Reset state after animation
      setTimeout(() => {
        setQuantity(1)
        setIsAdded(false)
      }, 200)
    }
  }
  
  /**
   * Handle adding item to cart
   * 
   * TODO: API INTEGRATION
   * After adding to cart, the cartSlice should sync with backend:
   * - POST /api/v1/cart/items
   * - Body: { bookId, quantity }
   */
  const handleAddToCart = () => {
    if (!book) return
    
    dispatch(addToCart({
      bookId: book.id,
      price: book.price,
      credits: book.credits,
      quantity,
    }))
    
    setIsAdded(true)
  }
  
  /**
   * Continue shopping - close modal
   */
  const handleContinueShopping = () => {
    onClose()
  }
  
  /**
   * Go to checkout
   */
  const handleGoToCheckout = () => {
    onClose()
    navigate('/checkout')
  }
  
  /**
   * Open cart sidebar
   */
  const handleViewCart = () => {
    onClose()
    onOpenCart?.()
  }
  
  if (!book) return null
  
  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        {!isAdded ? (
          // Add to Cart View
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ShoppingCart className="h-5 w-5" />
                Add to Cart
              </DialogTitle>
              <DialogDescription>
                Review your selection before adding to cart
              </DialogDescription>
            </DialogHeader>
            
            <div className="flex gap-4 py-4">
              {/* Book Cover */}
              <img
                src={book.coverImage || '/placeholder-cover.jpg'}
                alt={book.title}
                className="w-24 h-36 object-cover rounded-md shadow-md"
              />
              
              {/* Book Details */}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-lg line-clamp-2">{book.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">{book.author}</p>
                {book.narrator && (
                  <p className="text-xs text-muted-foreground">
                    Narrated by {book.narrator}
                  </p>
                )}
                
                <Separator className="my-3" />
                
                {/* Pricing */}
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-lg">{formatPrice(book.price)}</span>
                    {book.originalPrice && book.originalPrice > book.price && (
                      <span className="text-sm text-muted-foreground line-through">
                        {formatPrice(book.originalPrice)}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-primary">
                    or {book.credits} credit{book.credits !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            </div>
            
            <Separator />
            
            {/* Quantity Selector */}
            <div className="flex items-center justify-between py-4">
              <span className="font-medium">Quantity</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  disabled={quantity <= 1}
                >
                  <Minus className="h-4 w-4" />
                </Button>
                <span className="w-10 text-center font-medium">{quantity}</span>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setQuantity(quantity + 1)}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            {/* Already in cart notice */}
            {isInCart && (
              <div className="bg-primary/10 text-primary rounded-md p-3 text-sm mb-4">
                <Check className="h-4 w-4 inline mr-2" />
                This item is already in your cart. Adding more will increase the quantity.
              </div>
            )}
            
            {/* Actions */}
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleContinueShopping}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={handleAddToCart}
              >
                <ShoppingCart className="h-4 w-4 mr-2" />
                Add to Cart
              </Button>
            </div>
          </>
        ) : (
          // Added Confirmation View
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-green-600">
                <Check className="h-5 w-5" />
                Added to Cart!
              </DialogTitle>
              <DialogDescription>
                Your item has been added to the cart
              </DialogDescription>
            </DialogHeader>
            
            <div className="flex gap-4 py-4">
              {/* Book Cover */}
              <img
                src={book.coverImage || '/placeholder-cover.jpg'}
                alt={book.title}
                className="w-20 h-28 object-cover rounded-md shadow-md"
              />
              
              {/* Confirmation Details */}
              <div className="flex-1">
                <h3 className="font-semibold line-clamp-2">{book.title}</h3>
                <p className="text-sm text-muted-foreground">{book.author}</p>
                <p className="text-sm mt-2">
                  Quantity: <span className="font-medium">{quantity}</span>
                </p>
                <p className="text-sm">
                  Total: <span className="font-semibold">{formatPrice(book.price * quantity)}</span>
                </p>
              </div>
            </div>
            
            <Separator />
            
            {/* Next Steps */}
            <div className="space-y-3 pt-4">
              <Button
                className="w-full"
                onClick={handleGoToCheckout}
              >
                Proceed to Checkout
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={handleViewCart}
              >
                View Cart
              </Button>
              <Button
                variant="ghost"
                className="w-full"
                onClick={handleContinueShopping}
              >
                Continue Shopping
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default AddToCartModal
