/**
 * Cancel Subscription Modal
 * 
 * Multi-step cancellation flow with retention offers
 */

import React, { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { AlertTriangle, Check, X, Loader2, Heart, PartyPopper } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { 
  cancelSubscription, 
  resetCancellationFlow,
  selectCancellationStage,
  selectDiscountOffer,
  selectSubscription,
} from '@/store/slices/subscriptionSlice'
import { selectCurrentUser } from '@/store/slices/authSlice'
import { DiscountOfferCard } from './SubscriptionComponents'

interface CancelSubscriptionModalProps {
  open: boolean
  onClose: () => void
}

const CANCELLATION_REASONS = [
  { id: 'too_expensive', label: "It's too expensive" },
  { id: 'not_using', label: "I'm not using it enough" },
  { id: 'found_alternative', label: 'Found a better alternative' },
  { id: 'missing_features', label: 'Missing features I need' },
  { id: 'temporary', label: 'Just need a break' },
  { id: 'other', label: 'Other reason' },
]

export const CancelSubscriptionModal: React.FC<CancelSubscriptionModalProps> = ({
  open,
  onClose
}) => {
  const dispatch = useAppDispatch()
  const user = useAppSelector(selectCurrentUser)
  const subscription = useAppSelector(selectSubscription)
  const cancellationStage = useAppSelector(selectCancellationStage)
  const discountOffer = useAppSelector(selectDiscountOffer)
  
  const [selectedReason, setSelectedReason] = useState('')
  const [otherReason, setOtherReason] = useState('')
  const [loading, setLoading] = useState(false)
  
  const handleClose = () => {
    dispatch(resetCancellationFlow())
    setSelectedReason('')
    setOtherReason('')
    onClose()
  }
  
  const handleStartCancellation = async () => {
    if (!user?.id) return
    setLoading(true)
    
    await dispatch(cancelSubscription({
      userId: user.id,
      stage: 'initial',
    }))
    
    setLoading(false)
  }
  
  const handleSubmitReason = async () => {
    if (!user?.id || !selectedReason) return
    setLoading(true)
    
    const reason = selectedReason === 'other' ? otherReason : selectedReason
    
    await dispatch(cancelSubscription({
      userId: user.id,
      stage: 'reason_collected',
      reason,
    }))
    
    setLoading(false)
  }
  
  const handleAcceptDiscount = async () => {
    if (!user?.id) return
    setLoading(true)
    
    await dispatch(cancelSubscription({
      userId: user.id,
      stage: 'discount_offered',
      acceptDiscount: true,
    }))
    
    setLoading(false)
  }
  
  const handleDeclineDiscount = async () => {
    if (!user?.id) return
    setLoading(true)
    
    await dispatch(cancelSubscription({
      userId: user.id,
      stage: 'discount_offered',
      acceptDiscount: false,
    }))
    
    setLoading(false)
  }
  
  const handleFinalCancel = async () => {
    if (!user?.id) return
    setLoading(true)
    
    await dispatch(cancelSubscription({
      userId: user.id,
      stage: 'final_confirmation',
    }))
    
    setLoading(false)
  }
  
  // Render content based on stage
  const renderContent = () => {
    // Initial state - not started yet
    if (!cancellationStage) {
      return (
        <>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-5 w-5" />
              Cancel Your Subscription?
            </DialogTitle>
            <DialogDescription>
              We're sorry to see you thinking about leaving. Before you go, we'd love to understand 
              what we could do better.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              If you cancel:
            </p>
            <ul className="mt-2 space-y-1 text-sm">
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-500" />
                You'll keep access until your billing period ends
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-500" />
                Your audiobooks stay in your library forever
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-500" />
                Unused credits won't expire
              </li>
              <li className="flex items-center gap-2">
                <X className="h-4 w-4 text-red-500" />
                You won't receive monthly credits anymore
              </li>
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Keep My Subscription
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleStartCancellation}
              disabled={loading}
            >
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Continue Cancellation
            </Button>
          </DialogFooter>
        </>
      )
    }
    
    // Reason collection stage
    if (cancellationStage === 'reason_collected') {
      return (
        <>
          <DialogHeader>
            <DialogTitle>Help Us Improve</DialogTitle>
            <DialogDescription>
              {subscription.cancellationMessage}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <RadioGroup value={selectedReason} onValueChange={setSelectedReason}>
              {CANCELLATION_REASONS.map(reason => (
                <div key={reason.id} className="flex items-center space-x-2">
                  <RadioGroupItem value={reason.id} id={reason.id} />
                  <Label htmlFor={reason.id}>{reason.label}</Label>
                </div>
              ))}
            </RadioGroup>
            
            {selectedReason === 'other' && (
              <div className="space-y-2">
                <Label htmlFor="other-reason">Please tell us more:</Label>
                <Input
                  id="other-reason"
                  value={otherReason}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOtherReason(e.target.value)}
                  placeholder="What could we do better?"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Keep My Subscription
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleSubmitReason}
              disabled={loading || !selectedReason}
            >
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Continue
            </Button>
          </DialogFooter>
        </>
      )
    }
    
    // Discount offer stage
    if (cancellationStage === 'discount_offered' && discountOffer) {
      return (
        <>
          <DialogHeader>
            <DialogTitle className="text-center">
              Wait! We Have Something Special For You
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <DiscountOfferCard
              discountPercentage={discountOffer.discount_percentage}
              durationMonths={discountOffer.duration_months}
              originalPrice={discountOffer.original_price_display}
              discountedPrice={discountOffer.discounted_price_display}
              savings={discountOffer.savings_display}
              onAccept={handleAcceptDiscount}
              onDecline={handleDeclineDiscount}
              loading={loading}
            />
          </div>
        </>
      )
    }
    
    // Discount accepted stage
    if (cancellationStage === 'discount_accepted') {
      return (
        <>
          <DialogHeader>
            <DialogTitle className="flex items-center justify-center gap-2 text-green-600">
              <PartyPopper className="h-6 w-6" />
              Welcome Back!
            </DialogTitle>
            <DialogDescription className="text-center">
              {subscription.cancellationMessage}
            </DialogDescription>
          </DialogHeader>
          <div className="py-8 text-center">
            <Heart className="h-16 w-16 text-pink-500 mx-auto mb-4" />
            <p className="text-lg font-medium">Thank you for staying with us!</p>
            <p className="text-sm text-muted-foreground mt-2">
              Your discount has been applied and will be reflected in your next billing cycle.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={handleClose} className="w-full">
              Continue to Dashboard
            </Button>
          </DialogFooter>
        </>
      )
    }
    
    // Final confirmation stage
    if (cancellationStage === 'final_confirmation') {
      return (
        <>
          <DialogHeader>
            <DialogTitle className="text-amber-600">
              Are You Absolutely Sure?
            </DialogTitle>
            <DialogDescription>
              {subscription.cancellationMessage}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm text-amber-700">
                <strong>Last chance:</strong> You can always resubscribe later, 
                and we'll be here when you're ready to come back!
              </p>
            </div>
          </div>
          <DialogFooter className="flex-col gap-2 sm:flex-row">
            <Button 
              variant="default" 
              onClick={handleClose}
              className="flex-1"
            >
              <Heart className="h-4 w-4 mr-2" />
              Keep My Subscription
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleFinalCancel}
              disabled={loading}
              className="flex-1"
            >
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Yes, Cancel Subscription
            </Button>
          </DialogFooter>
        </>
      )
    }
    
    // Cancelled stage
    if (cancellationStage === 'cancelled') {
      return (
        <>
          <DialogHeader>
            <DialogTitle>Subscription Cancelled</DialogTitle>
            <DialogDescription>
              {subscription.cancellationMessage}
            </DialogDescription>
          </DialogHeader>
          <div className="py-6 text-center">
            <p className="text-sm text-muted-foreground">
              We hope to see you again soon! Remember, you can resubscribe anytime.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={handleClose} className="w-full">
              Close
            </Button>
          </DialogFooter>
        </>
      )
    }
    
    return null
  }
  
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="sm:max-w-md">
        {renderContent()}
      </DialogContent>
    </Dialog>
  )
}

export default CancelSubscriptionModal
