/**
 * PermissionGate Component
 * 
 * Conditional rendering component that only shows children if user
 * has the required permissions or role.
 * 
 * @author Andrew D'Angelo
 */

import React, { ReactNode } from 'react';
import { UserRole, Permission } from '@/types/permissions';
import { usePermissions } from '@/hooks/usePermissions';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Lock } from 'lucide-react';
import { Link } from 'react-router-dom';

interface PermissionGateProps {
  children: ReactNode;
  
  // Permission-based access
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean; // If true, user must have all permissions. If false, any permission
  
  // Role-based access
  role?: UserRole;
  
  // Fallback content
  fallback?: ReactNode;
  showUpgradePrompt?: boolean; // Show upgrade prompt instead of hiding content
}

export const PermissionGate: React.FC<PermissionGateProps> = ({
  children,
  permission,
  permissions,
  requireAll = true,
  role,
  fallback,
  showUpgradePrompt = false,
}) => {
  const {
    hasPermission,
    hasAllPermissions,
    hasAnyPermission,
    hasRole,
    checkPermission,
  } = usePermissions();

  let hasAccess = true;

  // Check single permission
  if (permission) {
    hasAccess = hasPermission(permission);
  }

  // Check multiple permissions
  if (permissions && permissions.length > 0) {
    hasAccess = requireAll 
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions);
  }

  // Check role
  if (role && hasAccess) {
    hasAccess = hasRole(role);
  }

  // User has access - render children
  if (hasAccess) {
    return <>{children}</>;
  }

  // User doesn't have access
  if (showUpgradePrompt && permission) {
    const permissionCheck = checkPermission(permission);
    
    return (
      <Alert className="border-primary/50 bg-primary/5">
        <Lock className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <div>
            <p className="font-medium">Upgrade Required</p>
            <p className="text-sm text-muted-foreground">
              {permissionCheck.reason}
            </p>
          </div>
          <Button asChild size="sm">
            <Link to="/pricing">Upgrade</Link>
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  // Render fallback or nothing
  return <>{fallback || null}</>;
};

export default PermissionGate;
