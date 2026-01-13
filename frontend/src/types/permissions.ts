/**
 * Permissions System Types
 * 
 * Defines user roles, subscription tiers, and permission management
 * for the Audiobooker platform.
 * 
 * @author Andrew D'Angelo
 */

// User subscription tiers
export enum SubscriptionTier {
  BASIC = 'basic',
  PREMIUM = 'premium',
  PUBLISHER = 'publisher',
  ENTERPRISE = 'enterprise',
}

// User roles (including admin)
export enum UserRole {
  BASIC = 'basic',
  PREMIUM = 'premium',
  PUBLISHER = 'publisher',
  ENTERPRISE = 'enterprise',
  ADMIN = 'admin',
}

// Specific permissions in the system
export enum Permission {
  // Library permissions
  VIEW_LIBRARY = 'view_library',
  UPLOAD_AUDIOBOOK = 'upload_audiobook',
  DELETE_AUDIOBOOK = 'delete_audiobook',
  
  // Store permissions
  BROWSE_STORE = 'browse_store',
  PURCHASE_AUDIOBOOK = 'purchase_audiobook',
  
  // Advanced features
  OFFLINE_DOWNLOAD = 'offline_download',
  HIGH_QUALITY_AUDIO = 'high_quality_audio',
  SYNC_DEVICES = 'sync_devices',
  
  // Publisher features
  PUBLISH_AUDIOBOOK = 'publish_audiobook',
  VIEW_ANALYTICS = 'view_analytics',
  MANAGE_PRICING = 'manage_pricing',
  BULK_UPLOAD = 'bulk_upload',
  
  // Enterprise features
  TEAM_MANAGEMENT = 'team_management',
  API_ACCESS = 'api_access',
  WHITE_LABEL = 'white_label',
  PRIORITY_SUPPORT = 'priority_support',
  CUSTOM_INTEGRATION = 'custom_integration',
  
  // Admin permissions
  MANAGE_USERS = 'manage_users',
  MANAGE_CONTENT = 'manage_content',
  VIEW_ALL_ANALYTICS = 'view_all_analytics',
  MANAGE_SUBSCRIPTIONS = 'manage_subscriptions',
  SYSTEM_SETTINGS = 'system_settings',
  MODERATION = 'moderation',
}

// Permission limits for different tiers
export interface TierLimits {
  maxUploads: number; // Max audiobooks that can be uploaded per month
  maxStorage: number; // Max storage in GB
  maxDevices: number; // Max number of devices for sync
  maxTeamMembers?: number; // Max team members (enterprise only)
  maxPublishedBooks?: number; // Max published books (publisher/enterprise)
}

// User permission data
export interface UserPermissions {
  role: UserRole;
  tier: SubscriptionTier | null;
  permissions: Permission[];
  limits: TierLimits;
  isAdmin: boolean;
}

// Permission check result
export interface PermissionCheckResult {
  allowed: boolean;
  reason?: string;
  upgradeRequired?: SubscriptionTier;
}
