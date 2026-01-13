/**
 * Permissions Context
 * 
 * Provides permission and role data throughout the application.
 * Integrates with authentication to manage user access control.
 * 
 * @author Andrew D'Angelo
 */

import React, { createContext, useContext, ReactNode, useMemo } from 'react';
import { UserRole, Permission, UserPermissions } from '@/types/permissions';
import { ROLE_PERMISSIONS, TIER_LIMITS } from '@/constants/permissions';

interface PermissionsContextType {
  userPermissions: UserPermissions | null;
  hasPermission: (permission: Permission) => boolean;
  hasRole: (role: UserRole) => boolean;
  canAccess: (requiredPermissions: Permission[]) => boolean;
}

const PermissionsContext = createContext<PermissionsContextType | undefined>(undefined);

interface PermissionsProviderProps {
  children: ReactNode;
  // TODO: Replace with actual user from auth context
  userRole?: UserRole;
  isAdmin?: boolean;
}

export const PermissionsProvider: React.FC<PermissionsProviderProps> = ({ 
  children,
  userRole = UserRole.BASIC,
  isAdmin = false,
}) => {
  // TODO: API Integration - Fetch user permissions from backend
  // GET /api/v1/users/me/permissions
  // Response should include: { role, tier, customPermissions, limits }

  const userPermissions = useMemo<UserPermissions>(() => {
    const permissions = isAdmin 
      ? Object.values(Permission)
      : ROLE_PERMISSIONS[userRole] || [];

    return {
      role: userRole,
      tier: isAdmin ? null : userRole as any,
      permissions,
      limits: TIER_LIMITS[userRole],
      isAdmin,
    };
  }, [userRole, isAdmin]);

  const hasPermission = (permission: Permission): boolean => {
    if (userPermissions.isAdmin) return true;
    return userPermissions.permissions.includes(permission);
  };

  const hasRole = (role: UserRole): boolean => {
    if (userPermissions.isAdmin) return true;
    
    const roleHierarchy = [
      UserRole.BASIC,
      UserRole.PREMIUM,
      UserRole.PUBLISHER,
      UserRole.ENTERPRISE,
      UserRole.ADMIN,
    ];
    
    const userRoleIndex = roleHierarchy.indexOf(userPermissions.role);
    const requiredRoleIndex = roleHierarchy.indexOf(role);
    
    return userRoleIndex >= requiredRoleIndex;
  };

  const canAccess = (requiredPermissions: Permission[]): boolean => {
    if (userPermissions.isAdmin) return true;
    return requiredPermissions.every(permission => 
      userPermissions.permissions.includes(permission)
    );
  };

  const value = {
    userPermissions,
    hasPermission,
    hasRole,
    canAccess,
  };

  return (
    <PermissionsContext.Provider value={value}>
      {children}
    </PermissionsContext.Provider>
  );
};

export const usePermissionsContext = () => {
  const context = useContext(PermissionsContext);
  if (context === undefined) {
    throw new Error('usePermissionsContext must be used within a PermissionsProvider');
  }
  return context;
};
