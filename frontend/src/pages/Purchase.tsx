import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { ArrowLeft, CreditCard, Lock, Check } from 'lucide-react';

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
  const [searchParams] = useSearchParams();
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'paypal'>('card');
  const [agreeToTerms, setAgreeToTerms] = useState(false);

  // Form state
  const [cardNumber, setCardNumber] = useState('');
  const [cardName, setCardName] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [cvv, setCvv] = useState('');
  const [billingZip, setBillingZip] = useState('');

  // Get purchase item from URL params
  const purchaseType = searchParams.get('type') as 'plan' | 'credits';
  const itemId = searchParams.get('id');
  const billingCycle = searchParams.get('cycle') as 'monthly' | 'annual' | null;

  // TODO: Replace with API call to fetch actual item details
  const [purchaseItem, setPurchaseItem] = useState<PurchaseItem | null>(null);

  useEffect(() => {
    // Mock data - replace with API call
    if (purchaseType === 'plan' && itemId) {
      const plans: Record<string, PurchaseItem> = {
        basic: {
          type: 'plan',
          id: 'basic',
          name: 'Basic Subscription',
          description: '1 Basic credit per month - Single voice narration',
          price: billingCycle === 'annual' ? 99.99 : 9.99,
          credits: 1,
          billingCycle: billingCycle || 'monthly'
        },
        premium: {
          type: 'plan',
          id: 'premium',
          name: 'Premium Subscription',
          description: '1 Premium credit per month - Multiple character voices',
          price: billingCycle === 'annual' ? 199.99 : 19.99,
          credits: 1,
          billingCycle: billingCycle || 'monthly'
        }
      };
      setPurchaseItem(plans[itemId] || null);
    } else if (purchaseType === 'credits' && itemId) {
      const creditPacks: Record<string, PurchaseItem> = {
        // Basic Credits
        'basic-1': { type: 'credits', id: 'basic-1', name: '1 Basic Credit', description: 'Single voice narration', price: 14.95, credits: 1 },
        'basic-3': { type: 'credits', id: 'basic-3', name: '3 Basic Credits', description: 'Single voice narration', price: 42.99, credits: 3 },
        'basic-5': { type: 'credits', id: 'basic-5', name: '5 Basic Credits', description: 'Single voice narration', price: 69.99, credits: 5 },
        'basic-10': { type: 'credits', id: 'basic-10', name: '10 Basic Credits', description: 'Single voice narration', price: 129.99, credits: 10 },
        // Premium Credits
        'premium-1': { type: 'credits', id: 'premium-1', name: '1 Premium Credit', description: 'Multiple character voices', price: 24.95, credits: 1 },
        'premium-3': { type: 'credits', id: 'premium-3', name: '3 Premium Credits', description: 'Multiple character voices', price: 71.99, credits: 3 },
        'premium-5': { type: 'credits', id: 'premium-5', name: '5 Premium Credits', description: 'Multiple character voices', price: 117.99, credits: 5 },
        'premium-10': { type: 'credits', id: 'premium-10', name: '10 Premium Credits', description: 'Multiple character voices', price: 229.99, credits: 10 }
      };
      setPurchaseItem(creditPacks[itemId] || null);
    }
  }, [purchaseType, itemId, billingCycle]);

  const handleSubmitPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!agreeToTerms) {
      alert('Please agree to the terms and conditions');
      return;
    }

    setIsProcessing(true);

    try {
      // TODO: API Integration
      // 1. Create payment intent
      // const paymentIntent = await fetch('/api/v1/payments/create-intent', {
      //   method: 'POST',
      //   body: JSON.stringify({
      //     type: purchaseItem?.type,
      //     itemId: purchaseItem?.id,
      //     amount: purchaseItem?.price,
      //     paymentMethod
      //   })
      // });

      // 2. Process payment with payment provider (Stripe, PayPal, etc.)
      
      // 3. Confirm payment on backend
      // await fetch('/api/v1/payments/confirm', {
      //   method: 'POST',
      //   body: JSON.stringify({ paymentIntentId: paymentIntent.id })
      // });

      // Mock success - simulate API delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Navigate to success page
      navigate('/purchase/success', { 
        state: { 
          item: purchaseItem,
          purchaseDate: new Date().toISOString()
        } 
      });
    } catch (error) {
      console.error('Payment failed:', error);
      alert('Payment failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
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
            <CardContent>
              <form onSubmit={handleSubmitPayment} className="space-y-6">
                {/* Payment Method Selection */}
                <div className="space-y-3">
                  <Label>Payment Method</Label>
                  <RadioGroup value={paymentMethod} onValueChange={(val) => setPaymentMethod(val as 'card' | 'paypal')}>
                    <div className="flex items-center space-x-2 border rounded-lg p-4">
                      <RadioGroupItem value="card" id="card" />
                      <Label htmlFor="card" className="flex-1 cursor-pointer">
                        <div className="flex items-center gap-2">
                          <CreditCard className="h-5 w-5" />
                          <span>Credit/Debit Card</span>
                        </div>
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2 border rounded-lg p-4">
                      <RadioGroupItem value="paypal" id="paypal" />
                      <Label htmlFor="paypal" className="flex-1 cursor-pointer">
                        PayPal
                      </Label>
                    </div>
                  </RadioGroup>
                </div>

                {paymentMethod === 'card' && (
                  <>
                    {/* Card Number */}
                    <div className="space-y-2">
                      <Label htmlFor="cardNumber">Card Number</Label>
                      <Input
                        id="cardNumber"
                        placeholder="1234 5678 9012 3456"
                        value={cardNumber}
                        onChange={(e) => setCardNumber(e.target.value)}
                        maxLength={19}
                        required
                      />
                    </div>

                    {/* Card Holder Name */}
                    <div className="space-y-2">
                      <Label htmlFor="cardName">Cardholder Name</Label>
                      <Input
                        id="cardName"
                        placeholder="John Doe"
                        value={cardName}
                        onChange={(e) => setCardName(e.target.value)}
                        required
                      />
                    </div>

                    {/* Expiry and CVV */}
                    <div className="grid gap-4 grid-cols-3">
                      <div className="space-y-2 col-span-1">
                        <Label htmlFor="expiry">Expiry</Label>
                        <Input
                          id="expiry"
                          placeholder="MM/YY"
                          value={expiryDate}
                          onChange={(e) => setExpiryDate(e.target.value)}
                          maxLength={5}
                          required
                        />
                      </div>
                      <div className="space-y-2 col-span-1">
                        <Label htmlFor="cvv">CVV</Label>
                        <Input
                          id="cvv"
                          placeholder="123"
                          value={cvv}
                          onChange={(e) => setCvv(e.target.value)}
                          maxLength={4}
                          required
                        />
                      </div>
                      <div className="space-y-2 col-span-1">
                        <Label htmlFor="zip">ZIP Code</Label>
                        <Input
                          id="zip"
                          placeholder="12345"
                          value={billingZip}
                          onChange={(e) => setBillingZip(e.target.value)}
                          maxLength={10}
                          required
                        />
                      </div>
                    </div>
                  </>
                )}

                <Separator />

                {/* Terms and Conditions */}
                <div className="flex items-start space-x-2">
                  <Checkbox 
                    id="terms" 
                    checked={agreeToTerms}
                    onCheckedChange={(checked) => setAgreeToTerms(checked as boolean)}
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
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={isProcessing || !agreeToTerms}
                >
                  {isProcessing ? (
                    <>Processing...</>
                  ) : (
                    <>
                      <Lock className="h-4 w-4 mr-2" />
                      Complete Purchase ${purchaseItem.price.toFixed(2)}
                    </>
                  )}
                </Button>

                <p className="text-xs text-center text-muted-foreground">
                  <Lock className="h-3 w-3 inline mr-1" />
                  Your payment information is secure and encrypted
                </p>
              </form>
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
  );
}
