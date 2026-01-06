/**
 * usePermissions Hook
 * 
 * Custom hook for checking user permissions and role-based access control.
 * 
 * @author Andrew D'Angelo
 */

import { useMemo } from 'react';
import { UserRole, Permission, PermissionCheckResult } from '@/types/permissions';
import { ROLE_PERMISSIONS, TIER_LIMITS } from '@/constants/permissions';

// TODO: Replace with actual user context when auth is implemented
interface MockUser {
  role: UserRole;
  isAdmin: boolean;
}

export const usePermissions = () => {
  // TODO: API Integration - Get current user from auth context
  // const { user } = useAuth();
  
  // Mock user for development - replace with actual user from auth context
  const mockUser: MockUser = {
    role: UserRole.BASIC,
    isAdmin: false,
  };

  // Get all permissions for the current user's role
  const userPermissions = useMemo(() => {
    if (!mockUser) return [];
    return ROLE_PERMISSIONS[mockUser.role] || [];
  }, [mockUser]);

  // Get tier limits for the current user
  const userLimits = useMemo(() => {
    if (!mockUser) return TIER_LIMITS[UserRole.BASIC];
    return TIER_LIMITS[mockUser.role];
  }, [mockUser]);

  /**
   * Check if user has a specific permission
   */
  const hasPermission = (permission: Permission): boolean => {
    if (!mockUser) return false;
    if (mockUser.isAdmin) return true;
    return userPermissions.includes(permission);
  };

  /**
   * Check if user has all specified permissions
   */
  const hasAllPermissions = (permissions: Permission[]): boolean => {
    if (!mockUser) return false;
    if (mockUser.isAdmin) return true;
    return permissions.every(permission => userPermissions.includes(permission));
  };

  /**
   * Check if user has any of the specified permissions
   */
  const hasAnyPermission = (permissions: Permission[]): boolean => {
    if (!mockUser) return false;
    if (mockUser.isAdmin) return true;
    return permissions.some(permission => userPermissions.includes(permission));
  };

  /**
   * Check if user has a specific role or higher
   */
  const hasRole = (role: UserRole): boolean => {
    if (!mockUser) return false;
    if (mockUser.isAdmin) return true;
    
    const roleHierarchy = [
      UserRole.BASIC,
      UserRole.PREMIUM,
      UserRole.PUBLISHER,
      UserRole.ENTERPRISE,
      UserRole.ADMIN,
    ];
    
    const userRoleIndex = roleHierarchy.indexOf(mockUser.role);
    const requiredRoleIndex = roleHierarchy.indexOf(role);
    
    return userRoleIndex >= requiredRoleIndex;
  };

  /**
   * Check permission with detailed result
   */
  const checkPermission = (permission: Permission): PermissionCheckResult => {
    if (!mockUser) {
      return {
        allowed: false,
        reason: 'User not authenticated',
      };
    }

    if (mockUser.isAdmin) {
      return { allowed: true };
    }

    const allowed = userPermissions.includes(permission);
    
    if (!allowed) {
      // Find the minimum tier that has this permission
      const roleHierarchy = [
        UserRole.BASIC,
        UserRole.PREMIUM,
        UserRole.PUBLISHER,
        UserRole.ENTERPRISE,
      ];
      
      const upgradeRequired = roleHierarchy.find(role => 
        ROLE_PERMISSIONS[role].includes(permission)
      );

      return {
        allowed: false,
        reason: `This feature requires ${upgradeRequired} tier or higher`,
        upgradeRequired: upgradeRequired as any,
      };
    }

    return { allowed: true };
  };

  /**
   * Check if user is within usage limits
   */
  const isWithinLimit = (limitType: keyof typeof userLimits, currentUsage: number): boolean => {
    const limit = userLimits[limitType];
    
    // -1 means unlimited
    if (limit === -1) return true;
    
    return currentUsage < (limit as number);
  };

  return {
    // User info
    userRole: mockUser?.role,
    isAdmin: mockUser?.isAdmin || false,
    
    // Permissions
    permissions: userPermissions,
    limits: userLimits,
    
    // Permission checks
    hasPermission,
    hasAllPermissions,
    hasAnyPermission,
    hasRole,
    checkPermission,
    isWithinLimit,
  };
};
