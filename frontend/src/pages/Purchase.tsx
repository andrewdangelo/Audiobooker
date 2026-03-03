import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { ArrowLeft, CreditCard, Lock, Check, Loader2, AlertCircle } from 'lucide-react';
import { StripeProvider, StripeElementsWrapper, StripePaymentForm } from '@/components/payment';
import { paymentService } from '@/services/paymentService';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { selectCurrentUser } from '@/store/slices/authSlice';
import { purchaseSubscription } from '@/store/slices/subscriptionSlice';
import { toast } from 'sonner';

// TODO: API Integration
// POST /api/v1/payments/create-intent - Create payment intent
// POST /api/v1/payments/confirm - Confirm payment
// POST /api/v1/subscriptions/create - Create subscription
// GET /api/v1/pricing/plan/:id - Get plan details
// GET /api/v1/pricing/credits/:id - Get credit pack details

interface PurchaseItem {
  type: 'plan' | 'credits';
  id: string;
  name: string;
  description: string;
  price: number;
  credits?: number;
  billingCycle?: 'monthly' | 'annual';
}

export default function Purchase() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [searchParams] = useSearchParams();
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<'card'>('card');
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  
  // Stripe state
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [isLoadingPaymentIntent, setIsLoadingPaymentIntent] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  
  // User from Redux
  const user = useAppSelector(selectCurrentUser);

  // Get purchase item from URL params
  const purchaseType = searchParams.get('type') as 'plan' | 'credits';
  const itemId = searchParams.get('id');
  const billingCycle = searchParams.get('cycle') as 'monthly' | 'annual' | null;

  const [purchaseItem, setPurchaseItem] = useState<PurchaseItem | null>(null);

  useEffect(() => {
    const loadPurchaseItem = async () => {
      if (!purchaseType || !itemId) {
        setPurchaseItem(null);
        return;
      }

      try {
        if (purchaseType === 'plan') {
          const plans = await paymentService.getSubscriptionPlans();
          const plan = plans.find(candidate => candidate.id === itemId);
          if (!plan) {
            setPurchaseItem(null);
            return;
          }

          const resolvedBillingCycle = billingCycle || 'monthly';
          const price =
            (resolvedBillingCycle === 'annual' ? plan.annual_amount_cents : plan.monthly_amount_cents) / 100;

          setPurchaseItem({
            type: 'plan',
            id: plan.id,
            name: `${plan.name} Subscription`,
            description: `${plan.included_credits} ${plan.included_credit_type} credit per ${resolvedBillingCycle === 'annual' ? 'year' : 'month'} - ${plan.description}`,
            price,
            credits: plan.included_credits,
            billingCycle: resolvedBillingCycle,
          });
          return;
        }

        const pack = await paymentService.getCreditPack(itemId);
        setPurchaseItem({
          type: 'credits',
          id: pack.id,
          name: pack.name,
          description: pack.description,
          price: pack.amount_cents / 100,
          credits: pack.credits,
        });
      } catch (error) {
        console.error('Failed to load purchase item:', error);
        setPurchaseItem(null);
      }
    };

    loadPurchaseItem();
  }, [purchaseType, itemId, billingCycle]);

  // Create payment intent when card payment is selected — credits only (plans use subscription checkout)
  useEffect(() => {
    if (paymentMethod === 'card' && purchaseItem && purchaseItem.type !== 'plan' && user?.id && !clientSecret) {
      const createPaymentIntent = async () => {
        setIsLoadingPaymentIntent(true);
        setPaymentError(null);
        try {
          // Convert price to cents
          const amountCents = Math.round(purchaseItem.price * 100);
          
          // Determine credit type from item ID
          const creditType = purchaseItem.id.startsWith('premium') ? 'premium' : 'basic';
          
          const response = await paymentService.createPaymentIntent({
            user_id: user.id,
            amount: amountCents,
            currency: 'usd',
            metadata: {
              purchase_type: 'credits',
              item_id: purchaseItem.id,
              item_name: purchaseItem.name,
              credits: String(purchaseItem.credits || 0),
              credit_type: creditType,
            },
          });
          setClientSecret(response.client_secret);
          setPaymentId(response.payment_id);
        } catch (error) {
          console.error('Failed to create payment intent:', error);
          setPaymentError(error instanceof Error ? error.message : 'Failed to initialize payment');
        } finally {
          setIsLoadingPaymentIntent(false);
        }
      };
      createPaymentIntent();
    }
  }, [paymentMethod, purchaseItem, user?.id, clientSecret]);

  // Reset client secret when switching payment methods
  const handlePaymentMethodChange = (method: 'card') => {
    if (method !== paymentMethod) {
      setClientSecret(null);
      setPaymentId(null);
      setPaymentError(null);
    }
    setPaymentMethod(method);
  };

  // Handle plan subscription via Stripe checkout session
  const handleSubscribePlan = async () => {
    if (!user?.id || !purchaseItem) return;
    setIsProcessing(true);
    setPaymentError(null);
    try {
      const result = await dispatch(
        purchaseSubscription({
          userId: user.id,
          plan: purchaseItem.id as 'basic' | 'premium' | 'publisher',
          billingCycle: purchaseItem.billingCycle || 'monthly',
        })
      ).unwrap();

      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      } else if (result.already_subscribed) {
        toast.info('Already subscribed', { description: result.message });
        navigate('/credits');
      } else {
        toast.success('Subscribed!', { description: result.message });
        navigate('/credits');
      }
    } catch (err: any) {
      setPaymentError(err || 'Failed to start subscription');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle successful Stripe payment
  const handlePaymentSuccess = async (paymentIntentId: string) => {
    // For credit purchases: call the backend to synchronously write credits to the DB
    // before navigating to the success page (which re-fetches credits from DB).
    // This avoids the race condition where the Stripe webhook arrives after fetchUserCredits.
    if (purchaseItem?.type === 'credits') {
      try {
        await paymentService.completeCreditPurchase(paymentIntentId);
      } catch (err) {
        // Non-fatal: success page will still show and webhook may still fire
        console.error('completeCreditPurchase failed:', err);
      }
    }

    navigate('/purchase/success', { 
      state: { 
        item: purchaseItem,
        purchaseDate: new Date().toISOString(),
        paymentIntentId,
      } 
    });
  };

  if (!purchaseItem) {
    return (
      <div className="container max-w-2xl mx-auto py-16 px-4">
        <Card>
          <CardContent className="py-16 text-center">
            <p className="text-muted-foreground mb-4">Invalid purchase item</p>
            <Button onClick={() => navigate('/pricing')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Pricing
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <StripeProvider>
      <div className="container max-w-5xl mx-auto py-8 px-4">
        <div className="mb-6">
          <Button variant="ghost" onClick={() => navigate('/pricing')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Pricing
          </Button>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Payment Form */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Payment Details</CardTitle>
                <CardDescription>
                  Complete your purchase securely
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Payment Method Selection */}
                <div className="space-y-3">
                  <Label>Payment Method</Label>
                  <RadioGroup value={paymentMethod} onValueChange={(val) => handlePaymentMethodChange(val as 'card')}>
                    <div className="flex items-center space-x-2 border rounded-lg p-4">
                      <RadioGroupItem value="card" id="card" />
                      <Label htmlFor="card" className="flex-1 cursor-pointer">
                        <div className="flex items-center gap-2">
                          <CreditCard className="h-5 w-5" />
                          <span>Credit/Debit Card</span>
                        </div>
                      </Label>
                    </div>
                  </RadioGroup>
                </div>

                {/* Stripe Card Payment */}
                {paymentMethod === 'card' && (
                  <div className="space-y-4">
                    {!user?.id ? (
                      <div className="p-4 bg-muted/50 rounded-md text-center">
                        <p className="text-sm text-muted-foreground">
                          Please sign in to complete your purchase
                        </p>
                        <Button 
                          variant="outline" 
                          className="mt-2"
                          onClick={() => navigate('/login?redirect=/purchase')}
                        >
                          Sign In
                        </Button>
                      </div>
                    ) : purchaseItem.type === 'plan' ? (
                      /* Subscription plans go through Stripe Checkout — no embedded card form */
                      <div className="space-y-4">
                        {paymentError && (
                          <div className="p-4 bg-destructive/10 text-destructive rounded-md flex items-center gap-2">
                            <AlertCircle className="h-5 w-5" />
                            <span className="text-sm">{paymentError}</span>
                          </div>
                        )}
                        <div className="flex items-start space-x-2">
                          <Checkbox
                            id="terms"
                            checked={agreeToTerms}
                            onChange={(e) => setAgreeToTerms(e.target.checked)}
                          />
                          <label
                            htmlFor="terms"
                            className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                          >
                            I agree to the{' '}
                            <a href="/terms" className="text-primary underline" target="_blank">
                              Terms and Conditions
                            </a>{' '}
                            and{' '}
                            <a href="/privacy" className="text-primary underline" target="_blank">
                              Privacy Policy
                            </a>
                          </label>
                        </div>
                        <Button
                          className="w-full"
                          size="lg"
                          disabled={isProcessing || !agreeToTerms}
                          onClick={handleSubscribePlan}
                        >
                          {isProcessing ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Redirecting...
                            </>
                          ) : (
                            <>
                              <Lock className="h-4 w-4 mr-2" />
                              Subscribe — ${purchaseItem.price.toFixed(2)}/{purchaseItem.billingCycle === 'annual' ? 'yr' : 'mo'}
                            </>
                          )}
                        </Button>
                        <p className="text-xs text-center text-muted-foreground">
                          You will be redirected to Stripe to complete your subscription.
                        </p>
                      </div>
                    ) : isLoadingPaymentIntent ? (
                      <div className="p-4 bg-muted/50 rounded-md flex items-center justify-center">
                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                        <span className="text-sm text-muted-foreground">Initializing payment...</span>
                      </div>
                    ) : paymentError ? (
                      <div className="p-4 bg-destructive/10 text-destructive rounded-md flex items-center gap-2">
                        <AlertCircle className="h-5 w-5" />
                        <span className="text-sm">{paymentError}</span>
                      </div>
                    ) : clientSecret ? (
                      <>
                        {/* Terms and Conditions - before payment form */}
                        <div className="flex items-start space-x-2">
                          <Checkbox 
                            id="terms" 
                            checked={agreeToTerms}
                            onChange={(e) => setAgreeToTerms(e.target.checked)}
                          />
                          <label
                            htmlFor="terms"
                            className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                          >
                            I agree to the{' '}
                            <a href="/terms" className="text-primary underline" target="_blank">
                              Terms and Conditions
                            </a>{' '}
                            and{' '}
                            <a href="/privacy" className="text-primary underline" target="_blank">
                              Privacy Policy
                            </a>
                          </label>
                        </div>

                        {agreeToTerms ? (
                          <StripeElementsWrapper clientSecret={clientSecret}>
                            <StripePaymentForm
                              amount={Math.round(purchaseItem.price * 100)}
                              currency="usd"
                              onSuccess={handlePaymentSuccess}
                              onError={(error) => setPaymentError(error)}
                              returnUrl={`${window.location.origin}/purchase/success?purchase_type=credits&item_id=${purchaseItem.id}${paymentId ? `&payment_id=${paymentId}` : ''}`}
                              submitLabel={`Pay $${purchaseItem.price.toFixed(2)}`}
                            />
                          </StripeElementsWrapper>
                        ) : (
                          <div className="p-4 bg-muted/50 rounded-md text-center">
                            <p className="text-sm text-muted-foreground">
                              Please agree to the terms and conditions to continue
                            </p>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="p-4 bg-muted/50 rounded-md flex items-center justify-center">
                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                        <span className="text-sm text-muted-foreground">Loading...</span>
                      </div>
                    )}
                  </div>
                )}

                <p className="text-xs text-center text-muted-foreground">
                  <Lock className="h-3 w-3 inline mr-1" />
                  Your payment information is secure and encrypted
                </p>
              </CardContent>
            </Card>
          </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <Card className="sticky top-4">
            <CardHeader>
              <CardTitle>Order Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold">{purchaseItem.name}</h3>
                <p className="text-sm text-muted-foreground">
                  {purchaseItem.description}
                </p>
              </div>

              <Separator />

              {purchaseItem.type === 'plan' && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary" />
                    <span>{purchaseItem.credits} credits per {purchaseItem.billingCycle === 'monthly' ? 'month' : 'year'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary" />
                    <span>Recurring billing</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary" />
                    <span>Cancel anytime</span>
                  </div>
                </div>
              )}

              {purchaseItem.type === 'credits' && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary" />
                    <span>{purchaseItem.credits} credits</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary" />
                    <span>One-time payment</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary" />
                    <span>Never expires</span>
                  </div>
                </div>
              )}

              <Separator />

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Subtotal</span>
                  <span>${purchaseItem.price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Tax</span>
                  <span>$0.00</span>
                </div>
                <Separator />
                <div className="flex justify-between font-semibold text-lg">
                  <span>Total</span>
                  <span>${purchaseItem.price.toFixed(2)}</span>
                </div>
              </div>
            </CardContent>
            <CardFooter className="text-xs text-muted-foreground">
              {purchaseItem.type === 'plan' 
                ? `You will be charged $${purchaseItem.price.toFixed(2)} ${purchaseItem.billingCycle === 'monthly' ? 'monthly' : 'annually'} until you cancel.`
                : 'One-time payment. Credits never expire.'
              }
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
    </StripeProvider>
  );
}
