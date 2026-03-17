/**
 * Subscription Components
 * 
 * UI components for displaying and managing subscription status
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Crown, Star, Zap, X, Check, Gift, AlertCircle } from 'lucide-react'
import { useAppSelector } from '@/store/hooks'
import { selectSubscriptionPlan, selectSubscriptionStatus, selectIsSubscribed, selectDiscountApplied } from '@/store/slices/subscriptionSlice'

// ============================================================================
// SUBSCRIPTION BADGE
// ============================================================================

interface SubscriptionBadgeProps {
  className?: string
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export const SubscriptionBadge: React.FC<SubscriptionBadgeProps> = ({ 
  className = '',
  showLabel = true,
  size = 'md'
}) => {
  const plan = useAppSelector(selectSubscriptionPlan)
  const status = useAppSelector(selectSubscriptionStatus)
  const isSubscribed = useAppSelector(selectIsSubscribed)
  const discountApplied = useAppSelector(selectDiscountApplied)
  
  if (!isSubscribed || plan === 'none') {
    return null
  }
  
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-0.5',
    lg: 'text-base px-3 py-1',
  }
  
  const iconSize = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }
  
  const isPending = status === 'pending_cancellation'
  
  return (
    <Badge 
      className={`
        ${sizeClasses[size]}
        ${plan === 'premium' 
          ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white border-0' 
          : 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white border-0'
        }
        ${isPending ? 'opacity-75' : ''}
        ${className}
      `}
    >
      {plan === 'premium' ? (
        <Crown className={`${iconSize[size]} mr-1`} />
      ) : (
        <Zap className={`${iconSize[size]} mr-1`} />
      )}
      {showLabel && (
        <span>
          {plan.charAt(0).toUpperCase() + plan.slice(1)}
          {isPending && ' (Cancelling)'}
          {discountApplied && ' 🎁'}
        </span>
      )}
    </Badge>
  )
}

// ============================================================================
// SUBSCRIPTION STATUS CARD
// ============================================================================

interface SubscriptionStatusCardProps {
  className?: string
  onManage?: () => void
}

export const SubscriptionStatusCard: React.FC<SubscriptionStatusCardProps> = ({ 
  className = '',
  onManage 
}) => {
  const navigate = useNavigate()
  const plan = useAppSelector(selectSubscriptionPlan)
  const status = useAppSelector(selectSubscriptionStatus)
  const isSubscribed = useAppSelector(selectIsSubscribed)
  const discountApplied = useAppSelector(selectDiscountApplied)
  
  const subscription = useAppSelector(state => state.subscription)
  
  const handleManageClick = () => {
    if (onManage) {
      onManage()
    } else {
      navigate('/settings?tab=subscription')
    }
  }
  
  if (!isSubscribed) {
    return (
      <Card className={`border-dashed ${className}`}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Star className="h-5 w-5 text-muted-foreground" />
            No Active Subscription
          </CardTitle>
          <CardDescription>
            Subscribe to get monthly credits and premium features
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => navigate('/pricing')} className="w-full">
            View Plans
          </Button>
        </CardContent>
      </Card>
    )
  }
  
  const isPending = status === 'pending_cancellation'
  
  return (
    <Card className={`
      ${plan === 'premium' 
        ? 'border-purple-200 bg-gradient-to-br from-purple-50 to-pink-50' 
        : 'border-blue-200 bg-gradient-to-br from-blue-50 to-cyan-50'
      }
      ${className}
    `}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            {plan === 'premium' ? (
              <Crown className="h-5 w-5 text-purple-500" />
            ) : (
              <Zap className="h-5 w-5 text-blue-500" />
            )}
            {plan.charAt(0).toUpperCase() + plan.slice(1)} Plan
          </CardTitle>
          <SubscriptionBadge size="sm" showLabel={false} />
        </div>
        <CardDescription>
          {isPending ? (
            <span className="text-amber-600">
              Cancelling at period end
            </span>
          ) : (
            <span>
              {subscription.billingCycle === 'annual' ? 'Annual' : 'Monthly'} subscription
            </span>
          )}
          {discountApplied && (
            <span className="ml-2 text-green-600">
              <Gift className="h-3 w-3 inline mr-1" />
              50% discount applied
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {subscription.currentPeriodEnd && (
          <p className="text-sm text-muted-foreground">
            {isPending ? 'Access until: ' : 'Renews: '}
            {new Date(subscription.currentPeriodEnd).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
          </p>
        )}
        <Button 
          variant="outline" 
          onClick={handleManageClick} 
          className="w-full"
        >
          Manage Subscription
        </Button>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// ALREADY SUBSCRIBED ALERT
// ============================================================================

interface AlreadySubscribedAlertProps {
  plan: string
  message: string
  onViewSubscription?: () => void
}

export const AlreadySubscribedAlert: React.FC<AlreadySubscribedAlertProps> = ({
  plan,
  message,
  onViewSubscription
}) => {
  const navigate = useNavigate()
  
  return (
    <Card className="border-amber-200 bg-amber-50">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-amber-700">
          <AlertCircle className="h-5 w-5" />
          Already Subscribed ({plan.charAt(0).toUpperCase() + plan.slice(1)} Plan)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-amber-700">{message}</p>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={() => onViewSubscription ? onViewSubscription() : navigate('/settings?tab=subscription')}
            className="flex-1"
          >
            View Subscription
          </Button>
          <Button 
            variant="outline" 
            onClick={() => navigate('/credits')}
            className="flex-1"
          >
            Buy Credits Instead
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// DISCOUNT OFFER CARD
// ============================================================================

interface DiscountOfferCardProps {
  discountPercentage: number
  durationMonths: number
  originalPrice: string
  discountedPrice: string
  savings: string
  onAccept: () => void
  onDecline: () => void
  loading?: boolean
}

export const DiscountOfferCard: React.FC<DiscountOfferCardProps> = ({
  discountPercentage,
  durationMonths,
  originalPrice,
  discountedPrice,
  savings,
  onAccept,
  onDecline,
  loading = false
}) => {
  return (
    <Card className="border-green-200 bg-gradient-to-br from-green-50 to-emerald-50">
      <CardHeader className="pb-3 text-center">
        <div className="mx-auto mb-2">
          <Gift className="h-12 w-12 text-green-500" />
        </div>
        <CardTitle className="text-xl text-green-700">
          🎁 Special Offer Just For You!
        </CardTitle>
        <CardDescription className="text-green-600">
          Stay with us and save {discountPercentage}% for {durationMonths} months
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-center space-y-1">
          <div className="flex items-center justify-center gap-3">
            <span className="text-2xl text-muted-foreground line-through">{originalPrice}</span>
            <span className="text-4xl font-bold text-green-600">{discountedPrice}</span>
            <span className="text-muted-foreground">/month</span>
          </div>
          <p className="text-sm text-green-600 font-medium">
            You save {savings} per month for {durationMonths} months!
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button 
            onClick={onAccept} 
            className="flex-1 bg-green-600 hover:bg-green-700"
            disabled={loading}
          >
            <Check className="h-4 w-4 mr-2" />
            Accept Offer
          </Button>
          <Button 
            variant="outline" 
            onClick={onDecline}
            className="flex-1"
            disabled={loading}
          >
            <X className="h-4 w-4 mr-2" />
            No Thanks
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default SubscriptionBadge
