import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Check, Zap, Star, Loader2, AlertCircle } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { selectCurrentUser } from '@/store/slices/authSlice';
import { 
  selectIsSubscribed, 
  selectSubscriptionPlan, 
  selectSubscriptionStatus,
  purchaseSubscription,
  selectSubscription,
} from '@/store/slices/subscriptionSlice';
import { 
  SubscriptionBadge, 
  SubscriptionStatusCard, 
  AlreadySubscribedAlert 
} from '@/components/subscription/SubscriptionComponents';
import { toast } from 'sonner';

// TODO: API Integration
// GET /api/v1/pricing/plans - Fetch available plans
// GET /api/v1/pricing/credits - Fetch credit packages

interface PricingPlan {
  id: string;
  name: string;
  description: string;
  price: number;
  credits: number;
  features: string[];
  isPopular?: boolean;
  icon: 'basic' | 'premium' | 'pro';
}

interface CreditPackage {
  id: string;
  credits: number;
  price: number;
  bonus?: number;
  type?: 'basic' | 'premium';
}

export default function Pricing() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
  const [creditType, setCreditType] = useState<'basic' | 'premium'>('basic');
  const [purchaseLoading, setPurchaseLoading] = useState<string | null>(null);
  const [showAlreadySubscribed, setShowAlreadySubscribed] = useState(false);
  const [alreadySubscribedMessage, setAlreadySubscribedMessage] = useState('');
  
  // Redux selectors
  const user = useAppSelector(selectCurrentUser);
  const isSubscribed = useAppSelector(selectIsSubscribed);
  const currentPlan = useAppSelector(selectSubscriptionPlan);
  const subscriptionStatus = useAppSelector(selectSubscriptionStatus);
  const subscription = useAppSelector(selectSubscription);

  // TODO: Replace with API call
  const plans: PricingPlan[] = [
    {
      id: 'basic',
      name: 'Basic Subscription',
      description: 'Single voice narration',
      price: billingCycle === 'monthly' ? 9.99 : 99.99,
      credits: 1,
      icon: 'basic',
      features: [
        '1 Basic credit per month',
        'Single voice narration',
        'Standard processing speed',
        'MP3 format downloads',
        'Email support',
        'Basic voice options'
      ]
    },
    {
      id: 'premium',
      name: 'Premium Subscription',
      description: 'Multiple character voices',
      price: billingCycle === 'monthly' ? 19.99 : 199.99,
      credits: 1,
      icon: 'premium',
      isPopular: true,
      features: [
        '1 Premium credit per month',
        'Multiple character voices',
        'Priority processing',
        'Multiple format options',
        'Priority email support',
        'Advanced voice library',
        'Theatrical narration'
      ]
    }
  ];

  // TODO: Replace with API call - Basic Credits
  const basicCreditPackages: CreditPackage[] = [
    { id: 'basic-1', credits: 1, price: 14.95 },
    { id: 'basic-3', credits: 3, price: 42.99 },
    { id: 'basic-5', credits: 5, price: 69.99 },
    { id: 'basic-10', credits: 10, price: 129.99 }
  ];

  // TODO: Replace with API call - Premium Credits
  const premiumCreditPackages: CreditPackage[] = [
    { id: 'premium-1', credits: 1, price: 24.95 },
    { id: 'premium-3', credits: 3, price: 71.99 },
    { id: 'premium-5', credits: 5, price: 117.99 },
    { id: 'premium-10', credits: 10, price: 229.99 }
  ];

  const handleSelectPlan = async (planId: string) => {
    // Check if user is logged in
    if (!user?.id) {
      toast.error('Please log in to subscribe');
      navigate('/login?redirect=/pricing');
      return;
    }
    
    // Check if already subscribed (guard)
    if (isSubscribed) {
      if (currentPlan === planId) {
        // Same plan
        setAlreadySubscribedMessage(
          `You are already subscribed to the ${currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)} plan. ` +
          `Your subscription is active until ${subscription.currentPeriodEnd ? new Date(subscription.currentPeriodEnd).toLocaleDateString() : 'your next billing date'}.`
        );
        setShowAlreadySubscribed(true);
        return;
      } else {
        // Different plan
        setAlreadySubscribedMessage(
          `You are currently subscribed to the ${currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)} plan. ` +
          `Please manage your current subscription in Settings before switching plans.`
        );
        setShowAlreadySubscribed(true);
        return;
      }
    }
    
    // Process subscription purchase
    setPurchaseLoading(planId);
    
    try {
      const result = await dispatch(purchaseSubscription({
        userId: user.id,
        plan: planId as 'basic' | 'premium',
        billingCycle: billingCycle,
      })).unwrap();
      
      if (result.already_subscribed) {
        setAlreadySubscribedMessage(result.message);
        setShowAlreadySubscribed(true);
      } else {
        toast.success('Successfully subscribed!', {
          description: result.message,
        });
        navigate('/credits');
      }
    } catch (error: any) {
      toast.error('Subscription failed', {
        description: error || 'Please try again',
      });
    } finally {
      setPurchaseLoading(null);
    }
  };

  const handleBuyCreditPack = (packId: string) => {
    // Navigate to purchase page with credit pack details
    navigate(`/purchase?type=credits&id=${packId}`);
  };

  const getIconForPlan = (icon: string) => {
    switch (icon) {
      case 'basic':
        return <Zap className="h-8 w-8" />;
      case 'premium':
        return <Star className="h-8 w-8" />;
      default:
        return <Zap className="h-8 w-8" />;
    }
  };

  return (
    <div className="container max-w-7xl mx-auto py-8 px-4 space-y-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">Choose Your Plan</h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Select the perfect plan for your audiobook needs or purchase additional credits
        </p>
        {isSubscribed && (
          <div className="flex items-center justify-center gap-2">
            <span className="text-sm text-muted-foreground">Current plan:</span>
            <SubscriptionBadge size="md" />
          </div>
        )}
      </div>

      {/* Already Subscribed Alert */}
      {showAlreadySubscribed && (
        <AlreadySubscribedAlert
          plan={currentPlan}
          message={alreadySubscribedMessage}
          onViewSubscription={() => navigate('/settings?tab=subscription')}
        />
      )}

      {/* Current Subscription Card (if subscribed) */}
      {isSubscribed && (
        <SubscriptionStatusCard className="max-w-md mx-auto" />
      )}

      {/* Billing Cycle Toggle */}
      <div className="flex justify-center items-center gap-4">
        <Button
          variant={billingCycle === 'monthly' ? 'default' : 'outline'}
          onClick={() => setBillingCycle('monthly')}
        >
          Monthly
        </Button>
        <Button
          variant={billingCycle === 'annual' ? 'default' : 'outline'}
          onClick={() => setBillingCycle('annual')}
          className="relative"
        >
          Annual
          <Badge className="absolute -top-2 -right-2 bg-green-500">
            Save 20%
          </Badge>
        </Button>
      </div>

      {/* Subscription Plans */}
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <Card
            key={plan.id}
            className={`relative ${
              plan.isPopular
                ? 'border-primary shadow-lg scale-105'
                : 'border-border'
            }`}
          >
            {plan.isPopular && (
              <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary">
                Most Popular
              </Badge>
            )}
            
            <CardHeader>
              <div className="flex items-center justify-center w-16 h-16 mx-auto rounded-full bg-primary/10 text-primary mb-4">
                {getIconForPlan(plan.icon)}
              </div>
              <CardTitle className="text-2xl text-center">{plan.name}</CardTitle>
              <CardDescription className="text-center">
                {plan.description}
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Price */}
              <div className="text-center">
                <div className="text-4xl font-bold">
                  ${plan.price}
                  <span className="text-lg font-normal text-muted-foreground">
                    /{billingCycle === 'monthly' ? 'mo' : 'yr'}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {plan.credits} credits included
                </p>
              </div>

              <Separator />

              {/* Features */}
              <ul className="space-y-2">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <Check className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                    <span className="text-sm">{feature}</span>
                  </li>
                ))}
              </ul>
            </CardContent>

            <CardFooter>
              <Button
                className="w-full"
                variant={plan.isPopular ? 'default' : 'outline'}
                size="lg"
                onClick={() => handleSelectPlan(plan.id)}
                disabled={purchaseLoading === plan.id || (isSubscribed && currentPlan === plan.id)}
              >
                {purchaseLoading === plan.id ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : isSubscribed && currentPlan === plan.id ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Current Plan
                  </>
                ) : (
                  `Choose ${plan.name}`
                )}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      <Separator className="my-12" />

      {/* One-Time Credit Packages */}
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-3xl font-bold">One-Time Credit Purchase</h2>
          <p className="text-muted-foreground">
            Purchase additional credits as needed, no subscription required
          </p>
        </div>

        {/* Credit Type Selector */}
        <div className="flex justify-center items-center gap-4">
          <Button
            variant={creditType === 'basic' ? 'default' : 'outline'}
            onClick={() => setCreditType('basic')}
          >
            Basic Credits
          </Button>
          <Button
            variant={creditType === 'premium' ? 'default' : 'outline'}
            onClick={() => setCreditType('premium')}
          >
            Premium Credits
          </Button>
        </div>

        {/* Basic Credits */}
        {creditType === 'basic' && (
          <div className="grid gap-4 md:grid-cols-4">
            {basicCreditPackages.map((pack) => (
              <Card key={pack.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-center w-12 h-12 mx-auto rounded-full bg-blue-100 text-blue-600 mb-2">
                    <Zap className="h-6 w-6" />
                  </div>
                  <CardTitle className="text-center text-xl">
                    {pack.credits} Credit{pack.credits > 1 ? 's' : ''}
                  </CardTitle>
                  <CardDescription className="text-center">
                    Basic - Single Voice
                  </CardDescription>
                </CardHeader>
                <CardContent className="pb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">${pack.price}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                      ${(pack.price / pack.credits).toFixed(2)} per credit
                    </p>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => handleBuyCreditPack(pack.id)}
                  >
                    Buy Now
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        {/* Premium Credits */}
        {creditType === 'premium' && (
          <div className="grid gap-4 md:grid-cols-4">
            {premiumCreditPackages.map((pack) => (
              <Card key={pack.id} className="hover:shadow-md transition-shadow border-purple-200">
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-center w-12 h-12 mx-auto rounded-full bg-purple-100 text-purple-600 mb-2">
                    <Star className="h-6 w-6" />
                  </div>
                  <CardTitle className="text-center text-xl">
                    {pack.credits} Credit{pack.credits > 1 ? 's' : ''}
                  </CardTitle>
                  <CardDescription className="text-center">
                    Premium - Multiple Voices
                  </CardDescription>
                </CardHeader>
                <CardContent className="pb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">${pack.price}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                      ${(pack.price / pack.credits).toFixed(2)} per credit
                    </p>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => handleBuyCreditPack(pack.id)}
                  >
                    Buy Now
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* FAQ or Additional Info */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle>How Credits Work</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            <strong>1 Credit = 1 Audiobook Conversion</strong>
          </p>
          <p>
            Each credit allows you to convert one book into an audiobook. Choose between two types:
          </p>
          <div className="grid md:grid-cols-2 gap-4 my-4">
            <div className="border rounded-lg p-4 bg-blue-50">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-5 w-5 text-blue-600" />
                <h4 className="font-semibold">Basic Credits</h4>
              </div>
              <ul className="list-disc list-inside space-y-1 ml-2 text-muted-foreground">
                <li>Single professional voice narration</li>
                <li>Standard processing speed</li>
                <li>Perfect for most audiobooks</li>
                <li>$14.95 per credit or $9.99/month subscription</li>
              </ul>
            </div>
            <div className="border rounded-lg p-4 bg-purple-50">
              <div className="flex items-center gap-2 mb-2">
                <Star className="h-5 w-5 text-purple-600" />
                <h4 className="font-semibold">Premium Credits</h4>
              </div>
              <ul className="list-disc list-inside space-y-1 ml-2 text-muted-foreground">
                <li>Multiple character voices (theatrical)</li>
                <li>Priority processing</li>
                <li>Advanced voice library</li>
                <li>$24.95 per credit or $19.99/month subscription</li>
              </ul>
            </div>
          </div>
          <p className="text-muted-foreground">
            Credits never expire and can be used at any time. Subscription credits renew monthly 
            and can be accumulated.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
