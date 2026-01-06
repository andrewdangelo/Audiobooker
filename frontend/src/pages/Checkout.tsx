/**
 * Checkout Page
 * 
 * Multi-step checkout flow for purchasing audiobooks.
 * Steps: Cart Overview → Payment Selection → Confirmation → Success
 * 
 * @author Andrew D'Angelo
 * 
 * FEATURES:
 * - Step 1 (Cart): View all items, adjust quantities, remove items
 * - Step 2 (Payment): Choose between credits or card payment
 * - Step 3 (Confirm): Review order before final purchase
 * - Success: Confirmation with link to library
 * 
 * API INTEGRATION POINTS:
 * - validateCart: Verify items availability and pricing before checkout
 * - checkout: Process the final purchase
 * - All integration points are marked with TODO comments
 */

import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  ShoppingCart,
  CreditCard,
  Coins,
  Check,
  CheckCircle2,
  Trash2,
  Plus,
  Minus,
  AlertCircle,
  Loader2,
  BookOpen,
  Receipt,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import {
  selectCartItems,
  selectCartItemCount,
  selectCartTotalPrice,
  selectCartTotalCredits,
  selectIsCartEmpty,
  selectCheckoutStep,
  selectIsCheckingOut,
  selectCartError,
  removeFromCart,
  updateCartQuantity,
  setCheckoutStep,
  resetCheckout,
  checkout,
} from '@/store/slices/cartSlice'
import { selectStoreBooks, selectUserCredits } from '@/store/slices/storeSlice'
import type { CartItem } from '@/store/slices/cartSlice'
import type { StoreBook } from '@/store/slices/storeSlice'

// ============================================================================
// TYPES
// ============================================================================

type CheckoutStepType = 'cart' | 'payment' | 'confirm' | 'success'

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
// STEP INDICATOR COMPONENT
// ============================================================================

interface StepIndicatorProps {
  currentStep: CheckoutStepType
}

const steps = [
  { id: 'cart', label: 'Cart', icon: ShoppingCart },
  { id: 'payment', label: 'Payment', icon: CreditCard },
  { id: 'confirm', label: 'Confirm', icon: Check },
]

function StepIndicator({ currentStep }: StepIndicatorProps) {
  const getStepStatus = (stepId: string): 'completed' | 'current' | 'upcoming' => {
    const stepOrder = ['cart', 'payment', 'confirm', 'success']
    const currentIndex = stepOrder.indexOf(currentStep)
    const stepIndex = stepOrder.indexOf(stepId)
    
    if (stepIndex < currentIndex) return 'completed'
    if (stepIndex === currentIndex) return 'current'
    return 'upcoming'
  }
  
  return (
    <div className="flex items-center justify-center mb-8">
      {steps.map((step, index) => {
        const status = getStepStatus(step.id)
        const Icon = step.icon
        
        return (
          <div key={step.id} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors',
                  status === 'completed' && 'bg-primary border-primary text-primary-foreground',
                  status === 'current' && 'border-primary text-primary',
                  status === 'upcoming' && 'border-muted-foreground/30 text-muted-foreground/50'
                )}
              >
                {status === 'completed' ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={cn(
                  'text-xs mt-1 font-medium',
                  status === 'current' && 'text-primary',
                  status === 'upcoming' && 'text-muted-foreground/50'
                )}
              >
                {step.label}
              </span>
            </div>
            
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'w-16 h-0.5 mx-2',
                  status === 'completed' ? 'bg-primary' : 'bg-muted-foreground/20'
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ============================================================================
// CART ITEM ROW COMPONENT
// ============================================================================

interface CheckoutCartItemProps {
  item: CartItemWithBook
  onRemove: () => void
  onUpdateQuantity: (quantity: number) => void
}

function CheckoutCartItem({ item, onRemove, onUpdateQuantity }: CheckoutCartItemProps) {
  const { book, quantity, priceAtAdd, creditsAtAdd } = item
  
  return (
    <div className="flex gap-4 py-4">
      {/* Book Cover */}
      <Link to={`/store/book/${book.id}`}>
        <img
          src={book.coverImage || '/placeholder-cover.jpg'}
          alt={book.title}
          className="w-20 h-28 object-cover rounded-md shadow-sm hover:shadow-md transition-shadow"
        />
      </Link>
      
      {/* Book Details */}
      <div className="flex-1 min-w-0">
        <Link to={`/store/book/${book.id}`} className="hover:underline">
          <h4 className="font-medium line-clamp-2">{book.title}</h4>
        </Link>
        <p className="text-sm text-muted-foreground">{book.author}</p>
        
        {/* Price */}
        <div className="mt-2 flex items-center gap-2 text-sm">
          <span className="font-semibold">{formatPrice(priceAtAdd)}</span>
          <span className="text-muted-foreground">or</span>
          <span className="text-primary font-medium">{creditsAtAdd} credit{creditsAtAdd !== 1 ? 's' : ''}</span>
        </div>
        
        {/* Quantity Controls */}
        <div className="mt-3 flex items-center gap-3">
          <div className="flex items-center border rounded-md">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-r-none"
              onClick={() => onUpdateQuantity(quantity - 1)}
              disabled={quantity <= 1}
            >
              <Minus className="h-3 w-3" />
            </Button>
            <span className="w-10 text-center text-sm font-medium">{quantity}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-l-none"
              onClick={() => onUpdateQuantity(quantity + 1)}
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={onRemove}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Remove
          </Button>
        </div>
      </div>
      
      {/* Line Total */}
      <div className="text-right">
        <p className="font-semibold">{formatPrice(priceAtAdd * quantity)}</p>
        <p className="text-sm text-primary">{creditsAtAdd * quantity} credits</p>
      </div>
    </div>
  )
}

// ============================================================================
// CART STEP COMPONENT
// ============================================================================

interface CartStepProps {
  items: CartItemWithBook[]
  totalPrice: number
  totalCredits: number
  onRemove: (bookId: string) => void
  onUpdateQuantity: (bookId: string, quantity: number) => void
  onNext: () => void
}

function CartStep({ items, totalPrice, totalCredits, onRemove, onUpdateQuantity, onNext }: CartStepProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" />
            Your Cart
          </CardTitle>
          <CardDescription>
            Review your items before proceeding to payment
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            {items.map((item) => (
              <CheckoutCartItem
                key={item.bookId}
                item={item}
                onRemove={() => onRemove(item.bookId)}
                onUpdateQuantity={(qty) => onUpdateQuantity(item.bookId, qty)}
              />
            ))}
          </div>
        </CardContent>
      </Card>
      
      {/* Order Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Order Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Subtotal ({items.length} item{items.length !== 1 ? 's' : ''})</span>
            <span className="font-medium">{formatPrice(totalPrice)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Or pay with credits</span>
            <span className="font-medium text-primary">{totalCredits} credits</span>
          </div>
          <Separator />
          <div className="flex justify-between text-lg font-semibold">
            <span>Total</span>
            <span>{formatPrice(totalPrice)}</span>
          </div>
        </CardContent>
      </Card>
      
      {/* Actions */}
      <div className="flex justify-between">
        <Button variant="outline" asChild>
          <Link to="/store">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Continue Shopping
          </Link>
        </Button>
        <Button onClick={onNext}>
          Continue to Payment
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>
    </div>
  )
}

// ============================================================================
// PAYMENT STEP COMPONENT
// ============================================================================

interface PaymentStepProps {
  totalPrice: number
  totalCredits: number
  userCredits: number
  paymentMethod: 'credits' | 'card'
  onPaymentMethodChange: (method: 'credits' | 'card') => void
  onBack: () => void
  onNext: () => void
}

function PaymentStep({
  totalPrice,
  totalCredits,
  userCredits,
  paymentMethod,
  onPaymentMethodChange,
  onBack,
  onNext,
}: PaymentStepProps) {
  const canUseCredits = userCredits >= totalCredits
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Payment Method
          </CardTitle>
          <CardDescription>
            Choose how you'd like to pay for your order
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={paymentMethod}
            onValueChange={(value: 'credits' | 'card') => onPaymentMethodChange(value)}
            className="space-y-4"
          >
            {/* Credits Option */}
            <div
              className={cn(
                'flex items-start space-x-4 p-4 border rounded-lg cursor-pointer transition-colors',
                paymentMethod === 'credits' && 'border-primary bg-primary/5',
                !canUseCredits && 'opacity-50 cursor-not-allowed'
              )}
              onClick={() => canUseCredits && onPaymentMethodChange('credits')}
            >
              <RadioGroupItem value="credits" id="credits" disabled={!canUseCredits} />
              <div className="flex-1">
                <Label htmlFor="credits" className="flex items-center gap-2 cursor-pointer">
                  <Coins className="h-5 w-5 text-primary" />
                  <span className="font-medium">Pay with Credits</span>
                </Label>
                <p className="text-sm text-muted-foreground mt-1">
                  Use your available credits to complete this purchase
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-sm">
                    Required: <span className="font-semibold text-primary">{totalCredits} credits</span>
                  </span>
                  <span className="text-sm">
                    Your balance: <span className="font-semibold">{userCredits} credits</span>
                  </span>
                </div>
                {!canUseCredits && (
                  <p className="text-sm text-destructive mt-2 flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    Insufficient credits
                  </p>
                )}
              </div>
            </div>
            
            {/* Card Option */}
            <div
              className={cn(
                'flex items-start space-x-4 p-4 border rounded-lg cursor-pointer transition-colors',
                paymentMethod === 'card' && 'border-primary bg-primary/5'
              )}
              onClick={() => onPaymentMethodChange('card')}
            >
              <RadioGroupItem value="card" id="card" />
              <div className="flex-1">
                <Label htmlFor="card" className="flex items-center gap-2 cursor-pointer">
                  <CreditCard className="h-5 w-5" />
                  <span className="font-medium">Pay with Card</span>
                </Label>
                <p className="text-sm text-muted-foreground mt-1">
                  Complete your purchase using a credit or debit card
                </p>
                <div className="mt-2">
                  <span className="text-sm">
                    Total: <span className="font-semibold">{formatPrice(totalPrice)}</span>
                  </span>
                </div>
                
                {/* Placeholder for card form */}
                {paymentMethod === 'card' && (
                  <div className="mt-4 p-4 bg-muted/50 rounded-md">
                    <p className="text-sm text-muted-foreground text-center">
                      {/* TODO: API INTEGRATION
                       * Integrate payment provider (Stripe, etc.) here
                       * - Initialize payment element
                       * - Handle card input
                       * - Process payment on checkout
                       */}
                      Payment form will be integrated here
                    </p>
                  </div>
                )}
              </div>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>
      
      {/* Actions */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Cart
        </Button>
        <Button onClick={onNext}>
          Review Order
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>
    </div>
  )
}

// ============================================================================
// CONFIRM STEP COMPONENT
// ============================================================================

interface ConfirmStepProps {
  items: CartItemWithBook[]
  totalPrice: number
  totalCredits: number
  paymentMethod: 'credits' | 'card'
  isProcessing: boolean
  error: string | null
  onBack: () => void
  onConfirm: () => void
}

function ConfirmStep({
  items,
  totalPrice,
  totalCredits,
  paymentMethod,
  isProcessing,
  error,
  onBack,
  onConfirm,
}: ConfirmStepProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            Order Review
          </CardTitle>
          <CardDescription>
            Please review your order before completing the purchase
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Items Summary */}
          <div>
            <h4 className="font-medium mb-3">Items ({items.length})</h4>
            <div className="space-y-3">
              {items.map((item) => (
                <div key={item.bookId} className="flex items-center gap-3">
                  <img
                    src={item.book.coverImage || '/placeholder-cover.jpg'}
                    alt={item.book.title}
                    className="w-12 h-16 object-cover rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm line-clamp-1">{item.book.title}</p>
                    <p className="text-xs text-muted-foreground">{item.book.author}</p>
                    <p className="text-xs">Qty: {item.quantity}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-sm">{formatPrice(item.priceAtAdd * item.quantity)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <Separator />
          
          {/* Payment Method */}
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Payment Method</span>
            <span className="font-medium flex items-center gap-2">
              {paymentMethod === 'credits' ? (
                <>
                  <Coins className="h-4 w-4 text-primary" />
                  Credits
                </>
              ) : (
                <>
                  <CreditCard className="h-4 w-4" />
                  Credit Card
                </>
              )}
            </span>
          </div>
          
          <Separator />
          
          {/* Order Total */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Subtotal</span>
              <span>{formatPrice(totalPrice)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tax</span>
              <span>$0.00</span>
            </div>
            <Separator />
            <div className="flex justify-between text-lg font-semibold">
              <span>Total</span>
              {paymentMethod === 'credits' ? (
                <span className="text-primary">{totalCredits} credits</span>
              ) : (
                <span>{formatPrice(totalPrice)}</span>
              )}
            </div>
          </div>
          
          {/* Error Message */}
          {error && (
            <div className="p-4 bg-destructive/10 text-destructive rounded-md flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Actions */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} disabled={isProcessing}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <Button 
          onClick={onConfirm} 
          disabled={isProcessing}
          size="lg"
          className="min-w-[180px]"
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Check className="h-4 w-4 mr-2" />
              Complete Purchase
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

// ============================================================================
// SUCCESS STEP COMPONENT
// ============================================================================

interface SuccessStepProps {
  itemCount: number
}

function SuccessStep({ itemCount }: SuccessStepProps) {
  return (
    <div className="text-center py-12">
      <div className="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
        <CheckCircle2 className="h-10 w-10 text-green-600 dark:text-green-400" />
      </div>
      
      <h2 className="text-2xl font-bold mb-2">Purchase Complete!</h2>
      <p className="text-muted-foreground mb-8">
        {itemCount} audiobook{itemCount !== 1 ? 's have' : ' has'} been added to your library
      </p>
      
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Button size="lg" asChild>
          <Link to="/library">
            <BookOpen className="h-4 w-4 mr-2" />
            Go to Library
          </Link>
        </Button>
        <Button variant="outline" size="lg" asChild>
          <Link to="/store">
            Continue Shopping
          </Link>
        </Button>
      </div>
    </div>
  )
}

// ============================================================================
// MAIN CHECKOUT PAGE
// ============================================================================

export default function Checkout() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  
  // Local state
  const [paymentMethod, setPaymentMethod] = useState<'credits' | 'card'>('card')
  const [purchasedCount, setPurchasedCount] = useState(0)
  
  // Redux state
  const cartItems = useAppSelector(selectCartItems)
  const storeBooks = useAppSelector(selectStoreBooks)
  const itemCount = useAppSelector(selectCartItemCount)
  const totalPrice = useAppSelector(selectCartTotalPrice)
  const totalCredits = useAppSelector(selectCartTotalCredits)
  const isEmpty = useAppSelector(selectIsCartEmpty)
  const currentStep = useAppSelector(selectCheckoutStep)
  const isCheckingOut = useAppSelector(selectIsCheckingOut)
  const checkoutError = useAppSelector(selectCartError)
  const userCredits = useAppSelector(selectUserCredits)
  
  // Join cart items with book data
  const itemsWithBooks: CartItemWithBook[] = cartItems
    .map((item: CartItem) => {
      const book = storeBooks.find((b: StoreBook) => b.id === item.bookId)
      return book ? { ...item, book } : null
    })
    .filter((item): item is CartItemWithBook => item !== null)
  
  // Reset checkout when component mounts
  useEffect(() => {
    dispatch(resetCheckout())
  }, [dispatch])
  
  // Redirect to store if cart is empty (except on success)
  useEffect(() => {
    if (isEmpty && currentStep !== 'success') {
      navigate('/store')
    }
  }, [isEmpty, currentStep, navigate])
  
  /**
   * Handle remove item from cart
   * 
   * TODO: API INTEGRATION
   * After removing, sync cart state with backend:
   * DELETE /api/v1/cart/items/:bookId
   */
  const handleRemove = (bookId: string) => {
    dispatch(removeFromCart(bookId))
  }
  
  /**
   * Handle quantity update
   * 
   * TODO: API INTEGRATION
   * After updating, sync cart state with backend:
   * PATCH /api/v1/cart/items/:bookId
   * Body: { quantity }
   */
  const handleUpdateQuantity = (bookId: string, quantity: number) => {
    if (quantity <= 0) {
      dispatch(removeFromCart(bookId))
    } else {
      dispatch(updateCartQuantity({ bookId, quantity }))
    }
  }
  
  /**
   * Navigate to next step
   */
  const handleNextStep = () => {
    const stepOrder: CheckoutStepType[] = ['cart', 'payment', 'confirm', 'success']
    const currentIndex = stepOrder.indexOf(currentStep)
    if (currentIndex < stepOrder.length - 1) {
      dispatch(setCheckoutStep(stepOrder[currentIndex + 1]))
    }
  }
  
  /**
   * Navigate to previous step
   */
  const handlePrevStep = () => {
    const stepOrder: CheckoutStepType[] = ['cart', 'payment', 'confirm', 'success']
    const currentIndex = stepOrder.indexOf(currentStep)
    if (currentIndex > 0) {
      dispatch(setCheckoutStep(stepOrder[currentIndex - 1]))
    }
  }
  
  /**
   * Handle final checkout
   * 
   * TODO: API INTEGRATION
   * This dispatches the checkout thunk which should:
   * 1. Validate cart items are still available
   * 2. Process payment (credits or card)
   * 3. Add books to user's library
   * 4. Return order confirmation
   * 
   * POST /api/v1/checkout
   * Body: { items, paymentMethod, paymentDetails? }
   */
  const handleCheckout = () => {
    setPurchasedCount(itemCount)
    dispatch(checkout({ paymentMethod }))
  }
  
  // Empty cart redirect handled above
  if (isEmpty && currentStep !== 'success') {
    return null
  }
  
  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Checkout</h1>
        <p className="text-muted-foreground mt-1">
          Complete your purchase
        </p>
      </div>
      
      {/* Step Indicator */}
      {currentStep !== 'success' && <StepIndicator currentStep={currentStep} />}
      
      {/* Step Content */}
      {currentStep === 'cart' && (
        <CartStep
          items={itemsWithBooks}
          totalPrice={totalPrice}
          totalCredits={totalCredits}
          onRemove={handleRemove}
          onUpdateQuantity={handleUpdateQuantity}
          onNext={handleNextStep}
        />
      )}
      
      {currentStep === 'payment' && (
        <PaymentStep
          totalPrice={totalPrice}
          totalCredits={totalCredits}
          userCredits={userCredits}
          paymentMethod={paymentMethod}
          onPaymentMethodChange={setPaymentMethod}
          onBack={handlePrevStep}
          onNext={handleNextStep}
        />
      )}
      
      {currentStep === 'confirm' && (
        <ConfirmStep
          items={itemsWithBooks}
          totalPrice={totalPrice}
          totalCredits={totalCredits}
          paymentMethod={paymentMethod}
          isProcessing={isCheckingOut}
          error={checkoutError}
          onBack={handlePrevStep}
          onConfirm={handleCheckout}
        />
      )}
      
      {currentStep === 'success' && (
        <SuccessStep itemCount={purchasedCount} />
      )}
    </div>
  )
}
