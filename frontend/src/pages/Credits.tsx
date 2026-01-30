import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Coins, ShoppingBag, Calendar, CreditCard, ArrowRight, Loader2, AlertCircle, Zap, Star } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { selectCurrentUser, selectAuthToken, fetchUserSubscription } from '@/store/slices/authSlice';
import { paymentService, type PaymentStatusResponse } from '@/services/paymentService';
import { authService } from '@/services/authService';
import { SubscriptionStatusCard } from '@/components/subscription/SubscriptionComponents';

export default function Credits() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectCurrentUser);
  const token = useAppSelector(selectAuthToken);
  
  const [basicCredits, setBasicCredits] = useState(0);
  const [premiumCredits, setPremiumCredits] = useState(0);
  const [paymentHistory, setPaymentHistory] = useState<PaymentStatusResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      console.log('User ID:', user?.id);
      console.log('Token from Redux:', token);
      
      if (!user?.id || !token) {
        console.log('Missing user ID or token, skipping fetch');
        return;
      }
      
      try {
        setIsLoading(true);
        setError(null);
        
        // Fetch credit breakdown
        console.log('Fetching credits with token:', token ? 'exists' : 'missing');
        const creditsData = await authService.getUserCredits(token);
        console.log('Credits data received:', creditsData);
        setBasicCredits(creditsData.basic_credits || 0);
        setPremiumCredits(creditsData.premium_credits || 0);
        
        // Fetch subscription status
        dispatch(fetchUserSubscription());
        
        // Fetch payment history
        const response = await paymentService.getUserPayments(user.id, 20);
        console.log('Payment history:', response);
        setPaymentHistory(response.payments);
      } catch (err) {
        console.error('Failed to fetch data:', err);
        setError('Failed to load credit information');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [user?.id, token, dispatch]);

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'N/A';
    }
  };

  const formatAmount = (cents: number) => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status.toLowerCase()) {
      case 'succeeded':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="container max-w-6xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Credits & Purchase History</h1>
        <p className="text-muted-foreground">
          Manage your credits and view your purchase history
        </p>
      </div>

      {/* Subscription Status Card */}
      <div className="mb-8">
        <SubscriptionStatusCard />
      </div>

      <div className="grid gap-6 md:grid-cols-3 mb-8">
        {/* Basic Credits Card */}
        <Card className="border-2 border-blue-200 bg-blue-50/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Zap className="h-4 w-4 text-blue-600" />
              Basic Credits
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center h-12 w-12 rounded-full bg-blue-100">
                <Zap className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <div className="text-3xl font-bold text-blue-900">{basicCredits}</div>
                <div className="text-sm text-muted-foreground">Single Voice</div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              For standard single-voice narration
            </p>
          </CardContent>
        </Card>

        {/* Premium Credits Card */}
        <Card className="border-2 border-purple-200 bg-purple-50/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Star className="h-4 w-4 text-purple-600" />
              Premium Credits
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center h-12 w-12 rounded-full bg-purple-100">
                <Star className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <div className="text-3xl font-bold text-purple-900">{premiumCredits}</div>
                <div className="text-sm text-muted-foreground">Multi-Voice</div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              For theatrical multi-character voices
            </p>
          </CardContent>
        </Card>

        {/* Total Credits Card */}
        <Card className="border-2 border-primary/20">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 mb-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-full bg-primary/10">
                <Coins className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="text-3xl font-bold">{basicCredits + premiumCredits}</div>
                <div className="text-sm text-muted-foreground">All Credits</div>
              </div>
            </div>
            <Separator className="mb-4" />
            <Button 
              className="w-full" 
              onClick={() => navigate('/pricing')}
            >
              <ShoppingBag className="h-4 w-4 mr-2" />
              Buy More Credits
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Quick Info */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Credit Types</CardTitle>
          <CardDescription>Understanding your credits</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="flex gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-full bg-blue-100 shrink-0">
                <Zap className="h-5 w-5 text-blue-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-1">Basic Credits</h4>
                <p className="text-sm text-muted-foreground">
                  Perfect for standard audiobooks with single voice narration. Great for most fiction and non-fiction content.
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-full bg-purple-100 shrink-0">
                <Star className="h-5 w-5 text-purple-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-1">Premium Credits</h4>
                <p className="text-sm text-muted-foreground">
                  Advanced theatrical narration with multiple character voices. Ideal for dialogue-heavy books and dramatic storytelling.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Usage Summary</CardTitle>
            <CardDescription>Your credit activity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Total Purchases</p>
                <p className="text-2xl font-bold">{paymentHistory.length}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Available Credits</p>
                <p className="text-2xl font-bold">{basicCredits + premiumCredits}</p>
              </div>
            </div>
            <Separator className="my-4" />
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Need more credits?</span>
              <Button variant="link" onClick={() => navigate('/pricing')} className="h-auto p-0">
                View Plans <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Credit Breakdown</CardTitle>
            <CardDescription>Your current balance by type</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Zap className="h-5 w-5 text-blue-600" />
                  <span className="font-medium">Basic Credits</span>
                </div>
                <span className="text-xl font-bold text-blue-900">{basicCredits}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Star className="h-5 w-5 text-purple-600" />
                  <span className="font-medium">Premium Credits</span>
                </div>
                <span className="text-xl font-bold text-purple-900">{premiumCredits}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Purchase History */}
      <Card>
        <CardHeader>
          <CardTitle>Purchase History</CardTitle>
          <CardDescription>
            Your recent credit purchases and transactions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12 text-destructive">
              <AlertCircle className="h-5 w-5 mr-2" />
              <span>{error}</span>
            </div>
          ) : paymentHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <ShoppingBag className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No purchases yet</h3>
              <p className="text-muted-foreground mb-6 max-w-sm">
                Get started by purchasing credits to create your audiobooks
              </p>
              <Button onClick={() => navigate('/pricing')}>
                View Pricing Plans
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-semibold">Date</th>
                    <th className="text-left py-3 px-4 font-semibold">Type</th>
                    <th className="text-left py-3 px-4 font-semibold">Credits</th>
                    <th className="text-left py-3 px-4 font-semibold">Amount</th>
                    <th className="text-left py-3 px-4 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paymentHistory.map((payment, index) => (
                    <tr key={payment.payment_id || `payment-${index}`} className="border-b last:border-0">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <span>{formatDate(payment.created_at)}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {payment.metadata?.credit_type === 'premium' ? (
                          <div className="flex items-center gap-2">
                            <div className="flex items-center justify-center h-6 w-6 rounded-full bg-purple-100">
                              <Star className="h-3 w-3 text-purple-600" />
                            </div>
                            <span className="font-medium">Premium</span>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-700">
                              Multi-Voice
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <div className="flex items-center justify-center h-6 w-6 rounded-full bg-blue-100">
                              <Zap className="h-3 w-3 text-blue-600" />
                            </div>
                            <span className="font-medium">Basic</span>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">
                              Single Voice
                            </span>
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Coins className="h-4 w-4 text-primary" />
                          <span className="font-semibold">+{payment.metadata?.credits || 0}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <CreditCard className="h-4 w-4 text-muted-foreground" />
                          <span>{formatAmount(payment.amount)}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadgeClass(payment.status)}`}>
                          {payment.status.charAt(0).toUpperCase() + payment.status.slice(1)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
