import { useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle, Home, Library, Receipt } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { selectUserCredits } from '@/store/slices/storeSlice';
import { fetchUserCredits, fetchUserSubscription } from '@/store/slices/authSlice';
import { clearCache } from '@/store/slices/audiobooksSlice';
import { paymentService } from '@/services/paymentService';
import { useState } from 'react';

interface ResolvedPurchaseData {
  item: {
    type: 'plan' | 'credits' | 'books'
    id: string
    name: string
    price: number
    credits?: number
    billingCycle?: 'monthly' | 'annual'
  }
  purchaseDate: string
}

export default function PurchaseSuccess() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [purchaseData, setPurchaseData] = useState<ResolvedPurchaseData | null>(location.state ?? null);
  const [isResolving, setIsResolving] = useState(!location.state);
  const currentCredits = useAppSelector(selectUserCredits);

  useEffect(() => {
    const resolvePurchaseData = async () => {
      if (purchaseData) {
        dispatch(fetchUserCredits());
        dispatch(fetchUserSubscription());
        setIsResolving(false);
        return;
      }

      const purchaseType = searchParams.get('purchase_type');
      const itemId = searchParams.get('item_id');
      const plan = searchParams.get('plan');
      const paymentId = searchParams.get('payment_id');
      const billingCycle = searchParams.get('billing_cycle') as 'monthly' | 'annual' | null;

      try {
        if (purchaseType === 'credits' && itemId) {
          const pack = await paymentService.getCreditPack(itemId);
          setPurchaseData({
            item: {
              type: 'credits',
              id: pack.id,
              name: pack.name,
              price: pack.amount_cents / 100,
              credits: pack.credits,
            },
            purchaseDate: new Date().toISOString(),
          });
        } else if (purchaseType === 'subscription' && plan) {
          const plans = await paymentService.getSubscriptionPlans();
          const selectedPlan = plans.find(candidate => candidate.id === plan);
          if (selectedPlan) {
            const resolvedBillingCycle = billingCycle || 'monthly';
            setPurchaseData({
              item: {
                type: 'plan',
                id: selectedPlan.id,
                name: `${selectedPlan.name} Subscription`,
                price: (
                  resolvedBillingCycle === 'annual'
                    ? selectedPlan.annual_amount_cents
                    : selectedPlan.monthly_amount_cents
                ) / 100,
                credits: selectedPlan.included_credits,
                billingCycle: resolvedBillingCycle,
              },
              purchaseDate: new Date().toISOString(),
            });
          }
        } else if (purchaseType === 'books' && paymentId) {
          const payment = await paymentService.getPaymentStatus(paymentId);
          const bookIds = payment.metadata?.book_ids?.split(',').filter(Boolean) || [];
          setPurchaseData({
            item: {
              type: 'books',
              id: payment.payment_id,
              name: bookIds.length > 1 ? `${bookIds.length} Audiobooks` : 'Audiobook Purchase',
              price: payment.amount_cents / 100,
            },
            purchaseDate: payment.created_at || new Date().toISOString(),
          });
          // Clear the audiobooks ownership cache so Library shows the
          // newly purchased title(s) on the very next visit.
          dispatch(clearCache());
        }
      } catch (error) {
        console.error('Failed to resolve purchase success details:', error);
      } finally {
        dispatch(fetchUserCredits());
        dispatch(fetchUserSubscription());
        setIsResolving(false);
      }
    };

    resolvePurchaseData();
  }, [dispatch, purchaseData, searchParams]);

  useEffect(() => {
    if (!isResolving && !purchaseData) {
      navigate('/pricing');
    }
  }, [isResolving, navigate, purchaseData]);

  if (isResolving || !purchaseData) {
    return null;
  }

  return (
    <div className="container max-w-2xl mx-auto py-16 px-4">
      <Card className="border-2 border-primary">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <div className="flex items-center justify-center w-20 h-20 rounded-full bg-primary/10">
              <CheckCircle className="h-12 w-12 text-primary" />
            </div>
          </div>
          <CardTitle className="text-3xl">Purchase Successful!</CardTitle>
          <CardDescription className="text-base">
            Thank you for your purchase. Your account has been updated.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          {/* Purchase Details */}
          <div className="bg-muted/50 rounded-lg p-6 space-y-3">
            <h3 className="font-semibold text-lg">Purchase Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Item:</span>
                <span className="font-medium">{purchaseData.item.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Amount:</span>
                <span className="font-medium">${purchaseData.item.price.toFixed(2)}</span>
              </div>
              {purchaseData.item.credits && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Credits Added:</span>
                  <span className="font-medium">{purchaseData.item.credits} credits</span>
                </div>
              )}
              {purchaseData.item.credits && (
                <div className="flex justify-between border-t pt-2 mt-2">
                  <span className="text-muted-foreground font-semibold">Current Balance:</span>
                  <span className="font-semibold text-primary">{currentCredits} credits</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Date:</span>
                <span className="font-medium">
                  {new Date(purchaseData.purchaseDate).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* What's Next */}
          <div className="space-y-3">
            <h3 className="font-semibold">What's Next?</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {purchaseData.item.credits && (
                <li className="text-primary font-medium">✓ Your account now has {currentCredits} credits available</li>
              )}
              <li>✓ A receipt has been sent to your email</li>
              <li>✓ You can start converting audiobooks immediately</li>
              {purchaseData.item.type === 'plan' && (
                <li>✓ Your subscription will renew automatically</li>
              )}
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="grid gap-3 sm:grid-cols-3 pt-4">
            <Button variant="outline" onClick={() => navigate('/dashboard')}>
              <Home className="h-4 w-4 mr-2" />
              Dashboard
            </Button>
            {purchaseData.item.type === 'books' ? (
              <Button variant="outline" onClick={() => navigate('/library')}>
                <Library className="h-4 w-4 mr-2" />
                My Library
              </Button>
            ) : (
              <Button variant="outline" onClick={() => navigate('/upload')}>
                <Library className="h-4 w-4 mr-2" />
                Upload Book
              </Button>
            )}
            <Button variant="outline" onClick={() => window.print()}>
              <Receipt className="h-4 w-4 mr-2" />
              Print Receipt
            </Button>
          </div>

          {purchaseData.item.type === 'books' ? (
            <Button 
              className="w-full" 
              size="lg"
              onClick={() => navigate('/library')}
            >
              <Library className="h-4 w-4 mr-2" />
              Go to Library
            </Button>
          ) : (
            <Button 
              className="w-full" 
              size="lg"
              onClick={() => navigate('/upload')}
            >
              Start Converting Audiobooks
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
