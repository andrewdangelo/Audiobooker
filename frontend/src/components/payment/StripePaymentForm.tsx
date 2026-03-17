/**
 * Stripe Payment Form
 * 
 * A payment form component using Stripe Elements.
 * Handles payment submission, processing states, and error display.
 */

import { useState, FormEvent } from 'react'
import { PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, CheckCircle, AlertCircle, CreditCard } from 'lucide-react'

// ============================================================================
// TYPES
// ============================================================================

type PaymentStatus = 'idle' | 'processing' | 'success' | 'error'

interface StripePaymentFormProps {
  amount: number
  currency?: string
  onSuccess?: (paymentIntent: string) => void
  onError?: (error: string) => void
  returnUrl?: string
  submitLabel?: string
}

// ============================================================================
// COMPONENT
// ============================================================================

export function StripePaymentForm({
  amount,
  currency = 'usd',
  onSuccess,
  onError,
  returnUrl,
  submitLabel,
}: StripePaymentFormProps) {
  const stripe = useStripe()
  const elements = useElements()
  
  const [status, setStatus] = useState<PaymentStatus>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Format amount for display
  const formattedAmount = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
  }).format(amount / 100)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()

    if (!stripe || !elements) {
      return
    }

    setStatus('processing')
    setErrorMessage(null)

    try {
      const { error, paymentIntent } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: returnUrl || `${window.location.origin}/checkout/success`,
        },
        redirect: 'if_required',
      })

      if (error) {
        setStatus('error')
        setErrorMessage(error.message || 'An error occurred during payment')
        onError?.(error.message || 'Payment failed')
      } else if (paymentIntent) {
        if (paymentIntent.status === 'succeeded') {
          setStatus('success')
          onSuccess?.(paymentIntent.id)
        } else if (paymentIntent.status === 'processing') {
          setStatus('processing')
        } else {
          setStatus('error')
          setErrorMessage(`Unexpected payment status: ${paymentIntent.status}`)
        }
      }
    } catch (err) {
      setStatus('error')
      const message = err instanceof Error ? err.message : 'Payment failed'
      setErrorMessage(message)
      onError?.(message)
    }
  }

  // Success state
  if (status === 'success') {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center">
        <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
        <h3 className="text-lg font-semibold text-green-700">Payment Successful!</h3>
        <p className="text-sm text-muted-foreground mt-2">
          Your payment of {formattedAmount} has been processed.
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Payment Amount */}
      <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
        <div className="flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Amount to pay</span>
        </div>
        <span className="text-lg font-semibold">{formattedAmount}</span>
      </div>

      {/* Stripe Payment Element */}
      <div className="p-4 border rounded-lg">
        <PaymentElement
          options={{
            layout: 'tabs',
            paymentMethodOrder: ['card', 'apple_pay', 'google_pay'],
          }}
        />
      </div>

      {/* Error Display */}
      {errorMessage && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      {/* Submit Button */}
      <Button
        type="submit"
        disabled={!stripe || !elements || status === 'processing'}
        className="w-full"
        size="lg"
      >
        {status === 'processing' ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          submitLabel || `Pay ${formattedAmount}`
        )}
      </Button>

      {/* Test Mode Notice */}
      <p className="text-xs text-center text-muted-foreground">
        Secure payment powered by Stripe
      </p>
    </form>
  )
}

export default StripePaymentForm
