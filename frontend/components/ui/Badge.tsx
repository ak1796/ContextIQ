import React from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'primary' | 'muted';

interface BadgeProps {
  children: React.ReactNode;
  /** Maps semantic intent to the design-system badge colours */
  variant?: BadgeVariant;
  className?: string;
}

const variantClass: Record<BadgeVariant, string> = {
  success: 'badge-success',
  warning: 'badge-warning',
  danger:  'badge-danger',
  info:    'badge-info',
  primary: 'badge-primary',
  muted:   'badge-muted',
};

export function Badge({ children, variant = 'primary', className }: BadgeProps) {
  return (
    <span className={cn('badge-base', variantClass[variant], className)}>
      {children}
    </span>
  );
}
