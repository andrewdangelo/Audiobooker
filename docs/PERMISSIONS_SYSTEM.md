# Permissions System Documentation

## Overview

The Audiobooker permissions system implements role-based access control (RBAC) with five distinct tiers:

1. **Basic** - Free tier with essential features
2. **Premium** - Enhanced features for enthusiasts
3. **Publisher** - Professional tools for content creators
4. **Enterprise** - Complete solution for organizations
5. **Admin** - Full system access and control

## Architecture

### Core Components

#### 1. Type Definitions (`/types/permissions.ts`)
- `UserRole` - Enum of all available roles
- `Permission` - Enum of all granular permissions
- `TierLimits` - Interface for usage limits per tier
- `UserPermissions` - Complete user permission data structure

#### 2. Permission Configuration (`/constants/permissions.ts`)
- `ROLE_PERMISSIONS` - Maps each role to its permissions
- `TIER_LIMITS` - Defines usage limits for each tier
- `TIER_NAMES` - Display names for tiers
- `TIER_PRICING` - Monthly pricing for each tier

#### 3. Permissions Hook (`/hooks/usePermissions.ts`)
Custom React hook for permission checks:
```typescript
const {
  userRole,
  isAdmin,
  permissions,
  limits,
  hasPermission,
  hasAllPermissions,
  hasAnyPermission,
  hasRole,
  checkPermission,
  isWithinLimit,
} = usePermissions();
```

#### 4. Permissions Context (`/contexts/PermissionsContext.tsx`)
Global context provider for permissions data (optional alternative to the hook).

#### 5. UI Components

**PermissionGate** (`/components/common/PermissionGate.tsx`)
- Conditionally renders children based on permissions
- Can show upgrade prompts
- Supports fallback content

**RoleBadge** (`/components/common/RoleBadge.tsx`)
- Displays user role as a styled badge
- Customizable with icons

## Usage Examples

### 1. Basic Permission Check

```typescript
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/types/permissions';

function UploadButton() {
  const { hasPermission } = usePermissions();
  
  if (!hasPermission(Permission.UPLOAD_AUDIOBOOK)) {
    return null; // Hide button if no permission
  }
  
  return <Button>Upload Audiobook</Button>;
}
```

### 2. Permission Gate Component

```typescript
import { PermissionGate } from '@/components/common/PermissionGate';
import { Permission } from '@/types/permissions';

function AnalyticsDashboard() {
  return (
    <PermissionGate 
      permission={Permission.VIEW_ANALYTICS}
      showUpgradePrompt={true}
    >
      <div>Analytics content here...</div>
    </PermissionGate>
  );
}
```

### 3. Role-Based Rendering

```typescript
import { usePermissions } from '@/hooks/usePermissions';
import { UserRole } from '@/types/permissions';

function TeamManagement() {
  const { hasRole } = usePermissions();
  
  if (!hasRole(UserRole.ENTERPRISE)) {
    return <UpgradePrompt tier={UserRole.ENTERPRISE} />;
  }
  
  return <TeamManagementPanel />;
}
```

### 4. Check Multiple Permissions

```typescript
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/types/permissions';

function PublisherDashboard() {
  const { hasAllPermissions } = usePermissions();
  
  const requiredPermissions = [
    Permission.PUBLISH_AUDIOBOOK,
    Permission.VIEW_ANALYTICS,
    Permission.MANAGE_PRICING,
  ];
  
  if (!hasAllPermissions(requiredPermissions)) {
    return <InsufficientPermissions />;
  }
  
  return <PublisherPanel />;
}
```

### 5. Usage Limits Check

```typescript
import { usePermissions } from '@/hooks/usePermissions';

function UploadForm() {
  const { limits, isWithinLimit } = usePermissions();
  const currentUploads = 42; // From API
  
  if (!isWithinLimit('maxUploads', currentUploads)) {
    return (
      <Alert>
        You've reached your upload limit of {limits.maxUploads} per month.
        <Button>Upgrade Plan</Button>
      </Alert>
    );
  }
  
  return <UploadFormContent />;
}
```

### 6. Display Role Badge

```typescript
import { RoleBadge } from '@/components/common/RoleBadge';
import { UserRole } from '@/types/permissions';

function UserProfile({ user }) {
  return (
    <div>
      <h2>{user.name}</h2>
      <RoleBadge role={user.role} showIcon={true} />
    </div>
  );
}
```

## Permission Categories

### Library Permissions
- `VIEW_LIBRARY` - View personal library
- `UPLOAD_AUDIOBOOK` - Upload audiobooks
- `DELETE_AUDIOBOOK` - Delete audiobooks

### Store Permissions
- `BROWSE_STORE` - Browse the store
- `PURCHASE_AUDIOBOOK` - Purchase audiobooks

### Advanced Features (Premium+)
- `OFFLINE_DOWNLOAD` - Download for offline
- `HIGH_QUALITY_AUDIO` - Access HD audio
- `SYNC_DEVICES` - Sync across devices

### Publisher Features
- `PUBLISH_AUDIOBOOK` - Publish to store
- `VIEW_ANALYTICS` - View sales analytics
- `MANAGE_PRICING` - Set pricing
- `BULK_UPLOAD` - Bulk upload tools

### Enterprise Features
- `TEAM_MANAGEMENT` - Manage team
- `API_ACCESS` - REST API access
- `WHITE_LABEL` - White labeling
- `PRIORITY_SUPPORT` - Priority support
- `CUSTOM_INTEGRATION` - Custom integrations

### Admin Permissions
- `MANAGE_USERS` - Manage all users
- `MANAGE_CONTENT` - Moderate content
- `VIEW_ALL_ANALYTICS` - System analytics
- `MANAGE_SUBSCRIPTIONS` - Manage billing
- `SYSTEM_SETTINGS` - System configuration
- `MODERATION` - Content moderation

## Tier Limits

| Tier       | Uploads/Month | Storage | Devices | Team Members | Published Books |
|------------|---------------|---------|---------|--------------|-----------------|
| Basic      | 5             | 5 GB    | 1       | -            | -               |
| Premium    | 50            | 50 GB   | 5       | -            | -               |
| Publisher  | 500           | 500 GB  | 10      | -            | 1000            |
| Enterprise | Unlimited     | Unlimited| Unlimited| 100         | Unlimited       |
| Admin      | Unlimited     | Unlimited| Unlimited| Unlimited   | Unlimited       |

## API Integration Points

### Required Backend Endpoints

1. **Get User Permissions**
   ```
   GET /api/v1/users/me/permissions
   Response: {
     role: string,
     tier: string,
     permissions: string[],
     limits: {
       maxUploads: number,
       maxStorage: number,
       maxDevices: number,
       ...
     },
     isAdmin: boolean
   }
   ```

2. **Check Permission**
   ```
   GET /api/v1/users/me/permissions/check?permission=UPLOAD_AUDIOBOOK
   Response: {
     allowed: boolean,
     reason?: string
   }
   ```

3. **Get Usage Stats**
   ```
   GET /api/v1/users/me/usage
   Response: {
     uploads: number,
     storageUsed: number,
     devicesConnected: number,
     ...
   }
   ```

4. **Upgrade Subscription**
   ```
   POST /api/v1/subscriptions/upgrade
   Body: { tier: string }
   ```

## Testing

Visit `/permissions-demo` to test the permissions system with interactive examples.

## Future Enhancements

- [ ] Custom permission sets for enterprise clients
- [ ] Temporary permission grants
- [ ] Permission delegation
- [ ] Audit logging for permission changes
- [ ] Role inheritance and custom roles
- [ ] Time-based permissions (trial periods)
