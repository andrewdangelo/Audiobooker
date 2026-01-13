/**
 * Permissions Demo Page
 * 
 * Demonstrates the permissions system with examples of gated content,
 * role badges, and upgrade prompts. Useful for testing and documentation.
 * 
 * @author Andrew D'Angelo
 */

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { PermissionGate } from '@/components/common/PermissionGate';
import { RoleBadge } from '@/components/common/RoleBadge';
import { usePermissions } from '@/hooks/usePermissions';
import { UserRole, Permission } from '@/types/permissions';
import { TIER_NAMES, TIER_DESCRIPTIONS, TIER_PRICING } from '@/constants/permissions';
import { Check, X } from 'lucide-react';

const PermissionsDemo = () => {
  const {
    userRole,
    isAdmin,
    permissions,
    limits,
    hasPermission,
    checkPermission,
  } = usePermissions();

  // Demo features to test permissions
  const demoFeatures = [
    {
      name: 'Upload Audiobook',
      permission: Permission.UPLOAD_AUDIOBOOK,
      description: 'Upload your own audiobook files',
    },
    {
      name: 'Offline Download',
      permission: Permission.OFFLINE_DOWNLOAD,
      description: 'Download audiobooks for offline listening',
    },
    {
      name: 'High Quality Audio',
      permission: Permission.HIGH_QUALITY_AUDIO,
      description: 'Access high-fidelity audio streams',
    },
    {
      name: 'Publish Audiobook',
      permission: Permission.PUBLISH_AUDIOBOOK,
      description: 'Publish audiobooks to the store',
    },
    {
      name: 'View Analytics',
      permission: Permission.VIEW_ANALYTICS,
      description: 'View detailed analytics and insights',
    },
    {
      name: 'Team Management',
      permission: Permission.TEAM_MANAGEMENT,
      description: 'Manage team members and permissions',
    },
    {
      name: 'API Access',
      permission: Permission.API_ACCESS,
      description: 'Access REST API for integrations',
    },
    {
      name: 'Manage Users',
      permission: Permission.MANAGE_USERS,
      description: 'Admin: Manage all users in the system',
    },
  ];

  return (
    <div className="container max-w-6xl py-6 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Permissions System Demo</h1>
        <p className="text-muted-foreground">
          Testing the role-based access control system
        </p>
      </div>

      {/* Current User Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Current User Status
            {userRole && <RoleBadge role={userRole} />}
          </CardTitle>
          <CardDescription>
            Your current role and permissions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Role</p>
              <p className="font-medium">{userRole ? TIER_NAMES[userRole] : 'Unknown'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Admin Status</p>
              <p className="font-medium">{isAdmin ? 'Yes' : 'No'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Max Uploads/Month</p>
              <p className="font-medium">{limits.maxUploads === -1 ? 'Unlimited' : limits.maxUploads}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Max Storage</p>
              <p className="font-medium">{limits.maxStorage === -1 ? 'Unlimited' : `${limits.maxStorage} GB`}</p>
            </div>
          </div>
          
          <Separator />
          
          <div>
            <p className="text-sm text-muted-foreground mb-2">Active Permissions ({permissions.length})</p>
            <div className="flex flex-wrap gap-1">
              {permissions.slice(0, 10).map(perm => (
                <Badge key={perm} variant="secondary" className="text-xs">
                  {perm.replace(/_/g, ' ')}
                </Badge>
              ))}
              {permissions.length > 10 && (
                <Badge variant="outline" className="text-xs">
                  +{permissions.length - 10} more
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Feature Access Matrix */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Access</CardTitle>
          <CardDescription>
            Test which features are available to your current role
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {demoFeatures.map(feature => {
              const hasAccess = hasPermission(feature.permission);
              const permCheck = checkPermission(feature.permission);
              
              return (
                <div 
                  key={feature.permission}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{feature.name}</p>
                      {hasAccess ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <X className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                    {!hasAccess && permCheck.reason && (
                      <p className="text-xs text-orange-600 mt-1">{permCheck.reason}</p>
                    )}
                  </div>
                  
                  {!hasAccess && (
                    <Button size="sm" variant="outline">
                      Upgrade
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Permission Gates Examples */}
      <Card>
        <CardHeader>
          <CardTitle>Permission Gates</CardTitle>
          <CardDescription>
            Components that conditionally render based on permissions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Basic visible to all */}
          <div className="p-4 rounded-lg border bg-green-50 dark:bg-green-950">
            <p className="font-medium">✓ This content is visible to everyone</p>
          </div>

          {/* Premium only */}
          <PermissionGate 
            permission={Permission.OFFLINE_DOWNLOAD}
            fallback={
              <div className="p-4 rounded-lg border bg-orange-50 dark:bg-orange-950">
                <p className="font-medium">✗ Premium feature - Not visible to basic users</p>
              </div>
            }
          >
            <div className="p-4 rounded-lg border bg-green-50 dark:bg-green-950">
              <p className="font-medium">✓ Premium Feature: Offline Downloads Available</p>
            </div>
          </PermissionGate>

          {/* Publisher only with upgrade prompt */}
          <PermissionGate 
            permission={Permission.PUBLISH_AUDIOBOOK}
            showUpgradePrompt={true}
          >
            <div className="p-4 rounded-lg border bg-green-50 dark:bg-green-950">
              <p className="font-medium">✓ Publisher Feature: You can publish audiobooks</p>
            </div>
          </PermissionGate>

          {/* Admin only */}
          <PermissionGate 
            permission={Permission.MANAGE_USERS}
            fallback={
              <div className="p-4 rounded-lg border bg-red-50 dark:bg-red-950">
                <p className="font-medium">✗ Admin Only - Not accessible</p>
              </div>
            }
          >
            <div className="p-4 rounded-lg border bg-green-50 dark:bg-green-950">
              <p className="font-medium">✓ Admin Feature: User Management Available</p>
            </div>
          </PermissionGate>
        </CardContent>
      </Card>

      {/* Tier Comparison */}
      <Card>
        <CardHeader>
          <CardTitle>Subscription Tiers</CardTitle>
          <CardDescription>
            Compare features across different tiers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[UserRole.BASIC, UserRole.PREMIUM, UserRole.PUBLISHER, UserRole.ENTERPRISE].map(role => (
              <div 
                key={role} 
                className={`p-4 rounded-lg border ${
                  role === userRole ? 'border-primary bg-primary/5' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{TIER_NAMES[role]}</h3>
                  <RoleBadge role={role} />
                </div>
                <p className="text-sm text-muted-foreground mb-3">
                  {TIER_DESCRIPTIONS[role]}
                </p>
                <p className="text-2xl font-bold mb-4">
                  ${TIER_PRICING[role as Exclude<UserRole, UserRole.ADMIN>]}
                  <span className="text-sm font-normal text-muted-foreground">/mo</span>
                </p>
                {role === userRole ? (
                  <Button className="w-full" variant="outline" disabled>
                    Current Plan
                  </Button>
                ) : (
                  <Button className="w-full">
                    Upgrade
                  </Button>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PermissionsDemo;
