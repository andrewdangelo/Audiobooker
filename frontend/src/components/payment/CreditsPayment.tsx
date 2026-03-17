/**
 * Credits Payment Component
 * 
 * Allows users to pay with their available credits balance.
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, CheckCircle, AlertCircle, Coins } from 'lucide-react'
import { paymentService } from '@/services/paymentService'

// ============================================================================
// TYPES
// ============================================================================

interface CreditsPaymentProps {
  userId: string
  amount: number
  currency?: string
  availableCredits: number
  metadata?: Record<string, string>
  onSuccess?: (orderId: string) => void
  onError?: (error: string) => void
}

// ============================================================================
// COMPONENT
// ============================================================================

export function CreditsPayment({
  userId,
  amount,
  currency = 'usd',
  availableCredits,
  metadata = {},
  onSuccess,
  onError,
}: CreditsPaymentProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Convert amount to credits (assuming 1 credit = 1 cent = 0.01 USD)
  const requiredCredits = amount

  // Format amounts for display
  const formattedAmount = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
  }).format(amount / 100)

  const hasEnoughCredits = availableCredits >= requiredCredits

  const handlePayWithCredits = async () => {
    if (!hasEnoughCredits) {
      setError('Insufficient credits balance')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      const response = await paymentService.payWithCredits({
        user_id: userId,
        amount,
        currency,
        metadata,
      })

      setIsSuccess(true)
      onSuccess?.(response.order_id)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Payment failed'
      setError(message)
      onError?.(message)
    } finally {
      setIsProcessing(false)
    }
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center">
        <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
        <h3 className="text-lg font-semibold text-green-700">Payment Successful!</h3>
        <p className="text-sm text-muted-foreground mt-2">
          {requiredCredits.toLocaleString()} credits have been deducted from your account.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Credits Balance Display */}
      <div className="p-4 bg-muted/50 rounded-lg space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Coins className="h-5 w-5 text-amber-500" />
            <span className="text-sm text-muted-foreground">Your credits balance</span>
          </div>
          <span className="font-semibold">{availableCredits.toLocaleString()} credits</span>
        </div>

        <div className="h-px bg-border" />

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Amount due</span>
          <span className="font-semibold">{formattedAmount}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Credits required</span>
          <span className="font-semibold">{requiredCredits.toLocaleString()} credits</span>
        </div>

        <div className="h-px bg-border" />

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Balance after payment</span>
          <span className={`font-semibold ${hasEnoughCredits ? 'text-green-600' : 'text-red-600'}`}>
            {hasEnoughCredits
              ? `${(availableCredits - requiredCredits).toLocaleString()} credits`
              : 'Insufficient'}
          </span>
        </div>
      </div>

      {/* Insufficient Credits Warning */}
      {!hasEnoughCredits && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            You need {(requiredCredits - availableCredits).toLocaleString()} more credits to complete this purchase.
          </AlertDescription>
        </Alert>
      )}

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Pay with Credits Button */}
      <Button
        onClick={handlePayWithCredits}
        disabled={!hasEnoughCredits || isProcessing}
        className="w-full"
        size="lg"
        variant={hasEnoughCredits ? 'default' : 'secondary'}
      >
        {isProcessing ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Coins className="mr-2 h-4 w-4" />
            Pay with Credits
          </>
        )}
      </Button>
    </div>
  )
}

export default CreditsPayment
