import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  glow?: boolean;
}

export function Card({ children, className, glow = false }: CardProps) {
  return (
    <div
      className={cn(
        'card',
        glow && 'hover:border-[color:var(--primary)] hover:shadow-lg',
        className
      )}
    >
      {children}
    </div>
  );
}
