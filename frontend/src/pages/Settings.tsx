import React, { useState } from 'react';
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

// Placeholder for user data - In a real app, this would come from a context or API
const initialUserData = {
  name: 'Andrew DAngelo',
  email: 'andrew@example.com',
  avatarUrl: 'https://github.com/shadcn.png',
  language: 'en',
  theme: 'system',
  notifications: {
    email: true,
    push: false,
    marketing: false,
  }
};

const Settings = () => {
  const [userData, setUserData] = useState(initialUserData);
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  // Handler for profile updates
  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // TODO: API Integration - Update User Profile
    // POST /api/v1/users/me
    // Body: { name: userData.name, email: userData.email }
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      toast({
        title: "Profile updated",
        description: "Your profile information has been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update profile. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handler for password update
  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // TODO: API Integration - Change Password
    // POST /api/v1/auth/change-password
    // Body: { currentPassword, newPassword }

    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast({
        title: "Password updated",
        description: "Your password has been changed successfully.",
      });
    } catch (error) {
      // Handle error
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

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="grid w-full grid-cols-4 lg:w-[400px]">
          <TabsTrigger value="profile">Profile</TabsTrigger>
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
                  fallback={userData.name.charAt(0)}
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
                <div className="grid gap-2">
                  <Label htmlFor="name">Display Name</Label>
                  <Input 
                    id="name" 
                    value={userData.name} 
                    onChange={(e) => setUserData({...userData, name: e.target.value})}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input 
                    id="email" 
                    type="email" 
                    value={userData.email} 
                    onChange={(e) => setUserData({...userData, email: e.target.value})}
                  />
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
                  <Input id="current-password" type="password" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="new-password">New Password</Label>
                  <Input id="new-password" type="password" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="confirm-password">Confirm Password</Label>
                  <Input id="confirm-password" type="password" />
                </div>
                <div className="flex justify-end">
                  <Button type="submit" disabled={isLoading}>Change Password</Button>
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
    </div>
  );
};

export default Settings;
