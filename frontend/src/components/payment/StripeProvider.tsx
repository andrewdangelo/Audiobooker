/**
 * Stripe Provider
 * 
 * Provides Stripe context to child components.
 * Fetches the publishable key from the payment service on mount.
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { loadStripe, Stripe } from '@stripe/stripe-js'
import { Elements } from '@stripe/react-stripe-js'
import { paymentService } from '@/services/paymentService'
import { STRIPE_PUBLISHABLE_KEY } from '@/config/env'

// ============================================================================
// TYPES
// ============================================================================

interface StripeContextValue {
  stripe: Stripe | null
  isLoading: boolean
  error: string | null
  mode: 'test' | 'live' | null
}

// ============================================================================
// CONTEXT
// ============================================================================

const StripeContext = createContext<StripeContextValue>({
  stripe: null,
  isLoading: true,
  error: null,
  mode: null,
})

export const useStripeContext = () => useContext(StripeContext)

// ============================================================================
// PROVIDER
// ============================================================================

interface StripeProviderProps {
  children: ReactNode
}

/**
 * StripeProvider initializes Stripe.js and provides it to child components.
 * 
 * It first tries to use VITE_STRIPE_PUBLISHABLE_KEY from environment,
 * otherwise fetches it from the payment service.
 */
export function StripeProvider({ children }: StripeProviderProps) {
  const [stripe, setStripe] = useState<Stripe | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'test' | 'live' | null>(null)

  useEffect(() => {
    const initStripe = async () => {
      try {
        let publishableKey = STRIPE_PUBLISHABLE_KEY

        // If no key in env, fetch from payment service
        if (!publishableKey) {
          const response = await paymentService.getPublishableKey()
          publishableKey = response.publishable_key
          setMode(response.mode)
        } else {
          // Determine mode from key prefix
          setMode(publishableKey.startsWith('pk_test_') ? 'test' : 'live')
        }

        if (!publishableKey) {
          throw new Error('Stripe publishable key not available')
        }

        const stripeInstance = await loadStripe(publishableKey)
        setStripe(stripeInstance)
      } catch (err) {
        console.error('Failed to initialize Stripe:', err)
        setError(err instanceof Error ? err.message : 'Failed to initialize Stripe')
      } finally {
        setIsLoading(false)
      }
    }

    initStripe()
  }, [])

  return (
    <StripeContext.Provider value={{ stripe, isLoading, error, mode }}>
      {children}
    </StripeContext.Provider>
  )
}

// ============================================================================
// ELEMENTS WRAPPER
// ============================================================================

interface StripeElementsWrapperProps {
  clientSecret: string
  children: ReactNode
}

/**
 * StripeElementsWrapper provides Stripe Elements context with a client secret.
 * Use this to wrap payment form components that need access to Stripe Elements.
 */
export function StripeElementsWrapper({ clientSecret, children }: StripeElementsWrapperProps) {
  const { stripe, isLoading, error } = useStripeContext()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
        <span className="ml-2 text-sm text-muted-foreground">Loading payment form...</span>
      </div>
    )
  }

  if (error || !stripe) {
    return (
      <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
        Failed to load payment form. Please refresh the page.
      </div>
    )
  }

  const options = {
    clientSecret,
    appearance: {
      theme: 'stripe' as const,
      variables: {
        colorPrimary: '#0f172a',
        colorBackground: '#ffffff',
        colorText: '#1e293b',
        colorDanger: '#ef4444',
        fontFamily: 'system-ui, sans-serif',
        borderRadius: '8px',
      },
    },
  }

  return (
    <Elements stripe={stripe} options={options}>
      {children}
    </Elements>
  )
}

export default StripeProvider
