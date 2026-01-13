/**
 * RoleBadge Component
 * 
 * Displays a user's role/tier as a styled badge.
 * 
 * @author Andrew D'Angelo
 */

import React from 'react';
import { UserRole } from '@/types/permissions';
import { Badge } from '@/components/ui/badge';
import { TIER_NAMES } from '@/constants/permissions';
import { Star, Briefcase, Building2, Shield } from 'lucide-react';

interface RoleBadgeProps {
  role: UserRole;
  showIcon?: boolean;
  className?: string;
}

const roleConfig = {
  [UserRole.BASIC]: {
    variant: 'secondary' as const,
    icon: null,
    color: 'text-muted-foreground',
  },
  [UserRole.PREMIUM]: {
    variant: 'default' as const,
    icon: Star,
    color: 'text-yellow-600',
  },
  [UserRole.PUBLISHER]: {
    variant: 'default' as const,
    icon: Briefcase,
    color: 'text-blue-600',
  },
  [UserRole.ENTERPRISE]: {
    variant: 'default' as const,
    icon: Building2,
    color: 'text-purple-600',
  },
  [UserRole.ADMIN]: {
    variant: 'destructive' as const,
    icon: Shield,
    color: 'text-red-600',
  },
};

export const RoleBadge: React.FC<RoleBadgeProps> = ({ 
  role, 
  showIcon = true,
  className = '',
}) => {
  const config = roleConfig[role];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={className}>
      {showIcon && Icon && (
        <Icon className={`h-3 w-3 mr-1 ${config.color}`} />
      )}
      {TIER_NAMES[role]}
    </Badge>
  );
};

export default RoleBadge;
