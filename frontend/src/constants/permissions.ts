/**
 * Permission Constants and Configuration
 * 
 * Defines permission mappings for each tier and role in the system.
 * 
 * @author Andrew D'Angelo
 */

import { UserRole, Permission, TierLimits } from '@/types/permissions';

// Permission mapping for each role
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  [UserRole.BASIC]: [
    Permission.VIEW_LIBRARY,
    Permission.BROWSE_STORE,
    Permission.PURCHASE_AUDIOBOOK,
    Permission.UPLOAD_AUDIOBOOK,
  ],
  
  [UserRole.PREMIUM]: [
    // All basic permissions
    Permission.VIEW_LIBRARY,
    Permission.BROWSE_STORE,
    Permission.PURCHASE_AUDIOBOOK,
    Permission.UPLOAD_AUDIOBOOK,
    Permission.DELETE_AUDIOBOOK,
    // Premium-specific permissions
    Permission.OFFLINE_DOWNLOAD,
    Permission.HIGH_QUALITY_AUDIO,
    Permission.SYNC_DEVICES,
  ],
  
  [UserRole.PUBLISHER]: [
    // All premium permissions
    Permission.VIEW_LIBRARY,
    Permission.BROWSE_STORE,
    Permission.PURCHASE_AUDIOBOOK,
    Permission.UPLOAD_AUDIOBOOK,
    Permission.DELETE_AUDIOBOOK,
    Permission.OFFLINE_DOWNLOAD,
    Permission.HIGH_QUALITY_AUDIO,
    Permission.SYNC_DEVICES,
    // Publisher-specific permissions
    Permission.PUBLISH_AUDIOBOOK,
    Permission.VIEW_ANALYTICS,
    Permission.MANAGE_PRICING,
    Permission.BULK_UPLOAD,
  ],
  
  [UserRole.ENTERPRISE]: [
    // All publisher permissions
    Permission.VIEW_LIBRARY,
    Permission.BROWSE_STORE,
    Permission.PURCHASE_AUDIOBOOK,
    Permission.UPLOAD_AUDIOBOOK,
    Permission.DELETE_AUDIOBOOK,
    Permission.OFFLINE_DOWNLOAD,
    Permission.HIGH_QUALITY_AUDIO,
    Permission.SYNC_DEVICES,
    Permission.PUBLISH_AUDIOBOOK,
    Permission.VIEW_ANALYTICS,
    Permission.MANAGE_PRICING,
    Permission.BULK_UPLOAD,
    // Enterprise-specific permissions
    Permission.TEAM_MANAGEMENT,
    Permission.API_ACCESS,
    Permission.WHITE_LABEL,
    Permission.PRIORITY_SUPPORT,
    Permission.CUSTOM_INTEGRATION,
  ],
  
  [UserRole.ADMIN]: [
    // All permissions including admin-only
    ...Object.values(Permission),
  ],
};

// Tier limits configuration
export const TIER_LIMITS: Record<UserRole, TierLimits> = {
  [UserRole.BASIC]: {
    maxUploads: 5, // 5 uploads per month
    maxStorage: 5, // 5 GB
    maxDevices: 1, // 1 device
  },
  
  [UserRole.PREMIUM]: {
    maxUploads: 50, // 50 uploads per month
    maxStorage: 50, // 50 GB
    maxDevices: 5, // 5 devices
  },
  
  [UserRole.PUBLISHER]: {
    maxUploads: 500, // 500 uploads per month
    maxStorage: 500, // 500 GB
    maxDevices: 10, // 10 devices
    maxPublishedBooks: 1000, // 1000 published books
  },
  
  [UserRole.ENTERPRISE]: {
    maxUploads: -1, // Unlimited
    maxStorage: -1, // Unlimited
    maxDevices: -1, // Unlimited
    maxTeamMembers: 100, // 100 team members
    maxPublishedBooks: -1, // Unlimited
  },
  
  [UserRole.ADMIN]: {
    maxUploads: -1, // Unlimited
    maxStorage: -1, // Unlimited
    maxDevices: -1, // Unlimited
    maxTeamMembers: -1, // Unlimited
    maxPublishedBooks: -1, // Unlimited
  },
};

// Tier names for display
export const TIER_NAMES: Record<UserRole, string> = {
  [UserRole.BASIC]: 'Basic',
  [UserRole.PREMIUM]: 'Premium',
  [UserRole.PUBLISHER]: 'Publisher',
  [UserRole.ENTERPRISE]: 'Enterprise',
  [UserRole.ADMIN]: 'Administrator',
};

// Tier descriptions
export const TIER_DESCRIPTIONS: Record<UserRole, string> = {
  [UserRole.BASIC]: 'Perfect for casual listeners',
  [UserRole.PREMIUM]: 'Enhanced features for audiobook enthusiasts',
  [UserRole.PUBLISHER]: 'Professional tools for content creators',
  [UserRole.ENTERPRISE]: 'Complete solution for organizations',
  [UserRole.ADMIN]: 'Full system access and control',
};

// Pricing information (monthly, in USD)
export const TIER_PRICING: Record<Exclude<UserRole, UserRole.ADMIN>, number> = {
  [UserRole.BASIC]: 0, // Free
  [UserRole.PREMIUM]: 9.99,
  [UserRole.PUBLISHER]: 49.99,
  [UserRole.ENTERPRISE]: 199.99,
};
