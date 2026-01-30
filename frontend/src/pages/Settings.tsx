import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/useToast';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { selectCurrentUser, selectAuthToken, updateUser, getUserDisplayName, fetchUserSubscription } from '@/store/slices/authSlice';
import { 
  selectSubscription, 
  selectIsSubscribed, 
  selectSubscriptionPlan,
  resubscribe,
} from '@/store/slices/subscriptionSlice';
import { authService } from '@/services/authService';
import { SubscriptionStatusCard, SubscriptionBadge } from '@/components/subscription/SubscriptionComponents';
import { CancelSubscriptionModal } from '@/components/subscription/CancelSubscriptionModal';
import { Crown, Zap, Calendar, CreditCard, AlertCircle } from 'lucide-react';

const Settings = () => {
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const user = useAppSelector(selectCurrentUser);
  const token = useAppSelector(selectAuthToken);
  const subscription = useAppSelector(selectSubscription);
  const isSubscribed = useAppSelector(selectIsSubscribed);
  const currentPlan = useAppSelector(selectSubscriptionPlan);
  
  // Get initial tab from URL query param
  const initialTab = searchParams.get('tab') || 'profile';
  const [activeTab, setActiveTab] = useState(initialTab);
  
  // Cancel subscription modal
  const [showCancelModal, setShowCancelModal] = useState(false);
  
  // Form state initialized from Redux user data
  const [userData, setUserData] = useState({
    name: getUserDisplayName(user),
    email: user?.email || '',
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    avatarUrl: user?.avatarUrl || 'https://github.com/shadcn.png',
    language: 'en',
    theme: 'system',
    notifications: {
      email: true,
      push: false,
      marketing: false,
    }
  });
  
  const [isLoading, setIsLoading] = useState(false);
  
  // Fetch subscription status on mount
  useEffect(() => {
    if (token) {
      dispatch(fetchUserSubscription());
    }
  }, [token, dispatch]);
  
  // Update form when user data changes
  useEffect(() => {
    if (user) {
      setUserData(prev => ({
        ...prev,
        name: getUserDisplayName(user),
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name || '',
        avatarUrl: user.avatarUrl || prev.avatarUrl,
      }));
    }
  }, [user]);
  
  // Handle resubscribe
  const handleResubscribe = async () => {
    if (!user?.id) return;
    
    try {
      await dispatch(resubscribe({
        userId: user.id,
        plan: currentPlan as 'basic' | 'premium',
        billingCycle: subscription.billingCycle || 'monthly',
      })).unwrap();
      
      toast({
        title: "Welcome back!",
        description: "Your subscription has been reactivated.",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error || "Failed to reactivate subscription.",
      });
    }
  };

  // Handler for profile updates
  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      if (token) {
        // Call API to update profile
        const updatedUser = await authService.updateProfile(token, {
          first_name: userData.first_name,
          last_name: userData.last_name,
        });
        
        // Update Redux store with new user data
        dispatch(updateUser({
          first_name: updatedUser.first_name,
          last_name: updatedUser.last_name,
        }));
      }
      
      toast({
        title: "Profile updated",
        description: "Your profile information has been updated successfully.",
      });
    } catch (error) {
      console.error('Profile update error:', error);
      toast({
        title: "Error",
        description: "Failed to update profile. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Password form state
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  // Handler for password update
  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast({
        title: "Error",
        description: "New passwords do not match.",
      });
      return;
    }
    
    if (passwordData.newPassword.length < 8) {
      toast({
        title: "Error",
        description: "Password must be at least 8 characters.",
      });
      return;
    }
    
    setIsLoading(true);

    try {
      if (token) {
        await authService.changePassword(
          token,
          passwordData.currentPassword,
          passwordData.newPassword
        );
      }
      
      toast({
        title: "Password updated",
        description: "Your password has been changed successfully.",
      });
      
      // Clear password fields
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || "Failed to update password. Please try again.";
      toast({
        title: "Error",
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-start min-h-screen bg-background">
      <div className="container max-w-4xl py-6 px-4 space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account settings and set e-mail preferences.
          </p>
        </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5 lg:w-[500px]">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="subscription">Subscription</TabsTrigger>
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        {/* Profile Settings */}
        <TabsContent value="profile" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>
                This is how others will see you on the site.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center space-x-4">
                <Avatar 
                  className="h-20 w-20" 
                  src={userData.avatarUrl} 
                  alt={userData.name}
                  fallback={userData.first_name?.charAt(0) || 'U'}
                />
                <Button variant="outline" size="sm">
                  Change Avatar
                  {/* TODO: API Integration - Upload Avatar 
                      POST /api/v1/users/me/avatar 
                      Multipart form data
                  */}
                </Button>
              </div>
              
              <Separator />

              <form onSubmit={handleProfileUpdate} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="first_name">First Name</Label>
                    <Input 
                      id="first_name" 
                      value={userData.first_name} 
                      onChange={(e) => setUserData({...userData, first_name: e.target.value})}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input 
                      id="last_name" 
                      value={userData.last_name} 
                      onChange={(e) => setUserData({...userData, last_name: e.target.value})}
                    />
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input 
                    id="email" 
                    type="email" 
                    value={userData.email} 
                    disabled
                    className="bg-muted"
                  />
                  <p className="text-sm text-muted-foreground">Email cannot be changed.</p>
                </div>
                <div className="flex justify-end">
                  <Button type="submit" disabled={isLoading}>
                    {isLoading ? "Saving..." : "Save Changes"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Subscription Settings */}
        <TabsContent value="subscription" className="space-y-4 mt-4">
          {/* Current Subscription Status */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {currentPlan === 'premium' ? (
                      <Crown className="h-5 w-5 text-purple-500" />
                    ) : currentPlan === 'basic' ? (
                      <Zap className="h-5 w-5 text-blue-500" />
                    ) : (
                      <CreditCard className="h-5 w-5" />
                    )}
                    Subscription
                  </CardTitle>
                  <CardDescription>
                    Manage your subscription plan and billing
                  </CardDescription>
                </div>
                {isSubscribed && <SubscriptionBadge />}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {isSubscribed ? (
                <>
                  {/* Subscription Details */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">Current Plan</Label>
                      <p className="font-medium">
                        {currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)} Plan
                      </p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">Billing Cycle</Label>
                      <p className="font-medium">
                        {subscription.billingCycle === 'annual' ? 'Annual' : 'Monthly'}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">Status</Label>
                      <p className="font-medium">
                        {subscription.status === 'pending_cancellation' ? (
                          <span className="text-amber-600">Cancelling at period end</span>
                        ) : (
                          <span className="text-green-600">Active</span>
                        )}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-sm text-muted-foreground">
                        {subscription.status === 'pending_cancellation' ? 'Access Until' : 'Next Billing Date'}
                      </Label>
                      <p className="font-medium flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        {subscription.currentPeriodEnd 
                          ? new Date(subscription.currentPeriodEnd).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric'
                            })
                          : 'Not available'
                        }
                      </p>
                    </div>
                  </div>
                  
                  {subscription.discountApplied && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <p className="text-sm text-green-700">
                        🎁 <strong>Loyalty Discount Applied:</strong> You're getting 50% off until{' '}
                        {subscription.discountEndDate 
                          ? new Date(subscription.discountEndDate).toLocaleDateString()
                          : 'the discount period ends'
                        }.
                      </p>
                    </div>
                  )}
                  
                  <Separator />
                  
                  {/* Actions */}
                  <div className="flex flex-col gap-3 sm:flex-row">
                    {subscription.status === 'pending_cancellation' ? (
                      <Button onClick={handleResubscribe} className="flex-1">
                        Reactivate Subscription
                      </Button>
                    ) : (
                      <>
                        <Button 
                          variant="outline" 
                          onClick={() => navigate('/pricing')}
                          className="flex-1"
                        >
                          Change Plan
                        </Button>
                        <Button 
                          variant="destructive" 
                          onClick={() => setShowCancelModal(true)}
                          className="flex-1"
                        >
                          Cancel Subscription
                        </Button>
                      </>
                    )}
                  </div>
                </>
              ) : (
                /* No Subscription */
                <div className="text-center py-6">
                  <div className="mx-auto w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                    <CreditCard className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-medium mb-2">No Active Subscription</h3>
                  <p className="text-muted-foreground mb-4">
                    Subscribe to get monthly credits and unlock premium features.
                  </p>
                  <Button onClick={() => navigate('/pricing')}>
                    View Plans
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* Subscription Benefits */}
          <Card>
            <CardHeader>
              <CardTitle>Subscription Benefits</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <h4 className="font-medium flex items-center gap-2">
                    <Zap className="h-4 w-4 text-blue-500" />
                    Basic Plan ($9.99/mo)
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                    <li>• 1 Basic credit per month</li>
                    <li>• Single voice narration</li>
                    <li>• Standard processing speed</li>
                    <li>• Email support</li>
                  </ul>
                </div>
                <div className="space-y-2">
                  <h4 className="font-medium flex items-center gap-2">
                    <Crown className="h-4 w-4 text-purple-500" />
                    Premium Plan ($19.99/mo)
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                    <li>• 1 Premium credit per month</li>
                    <li>• Multiple character voices</li>
                    <li>• Priority processing</li>
                    <li>• Priority support</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Account Settings */}
        <TabsContent value="account" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Password</CardTitle>
              <CardDescription>
                Change your password here. After saving, you'll be logged out.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePasswordUpdate} className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="current-password">Current Password</Label>
                  <Input 
                    id="current-password" 
                    type="password" 
                    value={passwordData.currentPassword}
                    onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="new-password">New Password</Label>
                  <Input 
                    id="new-password" 
                    type="password" 
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="confirm-password">Confirm Password</Label>
                  <Input 
                    id="confirm-password" 
                    type="password" 
                    value={passwordData.confirmPassword}
                    onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                  />
                </div>
                <div className="flex justify-end">
                  <Button type="submit" disabled={isLoading}>
                    {isLoading ? "Updating..." : "Change Password"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>
                Irreversible actions for your account.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="font-medium">Delete Account</p>
                  <p className="text-sm text-muted-foreground">
                    Permanently delete your account and all of your content.
                  </p>
                </div>
                <Button variant="destructive">Delete Account</Button>
                {/* TODO: API Integration - Delete Account
                    DELETE /api/v1/users/me
                */}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance Settings */}
        <TabsContent value="appearance" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>
                Customize the look and feel of the application.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="theme">Theme</Label>
                <Select defaultValue={userData.theme} onValueChange={(val) => setUserData({...userData, theme: val})}>
                  <SelectTrigger id="theme">
                    <SelectValue placeholder="Select theme" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="dark">Dark</SelectItem>
                    <SelectItem value="system">System</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  Select the theme for the dashboard.
                </p>
                {/* TODO: Integration - Theme Context
                    Connect this to the app's theme provider context
                */}
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="language">Language</Label>
                <Select defaultValue={userData.language} onValueChange={(val) => setUserData({...userData, language: val})}>
                  <SelectTrigger id="language">
                    <SelectValue placeholder="Select language" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="es">Spanish</SelectItem>
                    <SelectItem value="fr">French</SelectItem>
                  </SelectContent>
                </Select>
                {/* TODO: Integration - i18n
                    Connect this to the app's internationalization provider
                */}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Settings */}
        <TabsContent value="notifications" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>
                Configure how you receive notifications.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between space-x-2">
                <Label htmlFor="email-notifications" className="flex flex-col space-y-1">
                  <span>Email Notifications</span>
                  <span className="font-normal text-sm text-muted-foreground">Receive emails about your account activity.</span>
                </Label>
                <Checkbox 
                  id="email-notifications" 
                  checked={userData.notifications.email}
                  onChange={(e) => 
                    setUserData({
                      ...userData, 
                      notifications: { ...userData.notifications, email: e.target.checked }
                    })
                  }
                />
                {/* TODO: API Integration - Update Notification Preferences
                    PATCH /api/v1/users/me/preferences
                */}
              </div>
              <Separator />
              <div className="flex items-center justify-between space-x-2">
                <Label htmlFor="marketing-emails" className="flex flex-col space-y-1">
                  <span>Marketing Emails</span>
                  <span className="font-normal text-sm text-muted-foreground">Receive emails about new products, features, and more.</span>
                </Label>
                <Checkbox 
                  id="marketing-emails" 
                  checked={userData.notifications.marketing}
                  onChange={(e) => 
                    setUserData({
                      ...userData, 
                      notifications: { ...userData.notifications, marketing: e.target.checked }
                    })
                  }
                />
              </div>
            </CardContent>
            <CardFooter>
              <Button className="ml-auto" onClick={() => {
                 toast({ title: "Preferences saved", description: "Your notification preferences have been updated." })
              }}>
                Save Preferences
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
      </div>
      
      {/* Cancel Subscription Modal */}
      <CancelSubscriptionModal 
        open={showCancelModal} 
        onClose={() => setShowCancelModal(false)} 
      />
    </div>
  );
};

export default Settings;
