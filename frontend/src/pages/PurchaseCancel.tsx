import { useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function PurchaseCancel() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const purchaseType = searchParams.get('purchase_type')

  return (
    <div className="container max-w-2xl mx-auto py-16 px-4">
      <Card>
        <CardHeader className="text-center">
          <CardTitle>Checkout Cancelled</CardTitle>
          <CardDescription>
            {purchaseType === 'subscription'
              ? 'Your subscription checkout was cancelled before payment completed.'
              : 'Your purchase was cancelled before payment completed.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button onClick={() => navigate('/pricing')}>Back to Pricing</Button>
          <Button variant="outline" onClick={() => navigate('/credits')}>
            View Credits
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
