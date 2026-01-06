import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle, Home, Library, Receipt } from 'lucide-react';

export default function PurchaseSuccess() {
  const navigate = useNavigate();
  const location = useLocation();
  const purchaseData = location.state;

  useEffect(() => {
    // If no purchase data, redirect to pricing
    if (!purchaseData) {
      navigate('/pricing');
    }
  }, [purchaseData, navigate]);

  if (!purchaseData) {
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
              <li>✓ Your credits are now available in your account</li>
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
            <Button variant="outline" onClick={() => navigate('/upload')}>
              <Library className="h-4 w-4 mr-2" />
              Upload Book
            </Button>
            <Button variant="outline" onClick={() => window.print()}>
              <Receipt className="h-4 w-4 mr-2" />
              Print Receipt
            </Button>
          </div>

          <Button 
            className="w-full" 
            size="lg"
            onClick={() => navigate('/upload')}
          >
            Start Converting Audiobooks
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
