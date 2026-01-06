/**
 * PublishButton Component
 * 
 * Button component for publishing audiobooks to the store.
 * Only visible to users with PUBLISH_AUDIOBOOK permission.
 * 
 * @author Andrew D'Angelo
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { PermissionGate } from '@/components/common/PermissionGate';
import { Permission } from '@/types/permissions';
import { Store, Lock } from 'lucide-react';

interface PublishButtonProps {
  audiobookId: string;
  variant?: 'default' | 'outline' | 'secondary' | 'ghost';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  showIcon?: boolean;
}

export const PublishButton: React.FC<PublishButtonProps> = ({
  audiobookId,
  variant = 'default',
  size = 'default',
  className = '',
  showIcon = true,
}) => {
  const navigate = useNavigate();

  return (
    <PermissionGate 
      permission={Permission.PUBLISH_AUDIOBOOK}
      fallback={
        <Button 
          variant="outline" 
          size={size} 
          className={className}
          disabled
        >
          {showIcon && <Lock className="h-4 w-4 mr-2" />}
          Publish to Store
        </Button>
      }
    >
      <Button 
        variant={variant}
        size={size}
        className={className}
        onClick={() => navigate(`/publish/${audiobookId}`)}
      >
        {showIcon && <Store className="h-4 w-4 mr-2" />}
        Publish to Store
      </Button>
    </PermissionGate>
  );
};

export default PublishButton;
