import React from 'react';
import { Card } from '@/components/ui/Card';
import { LucideIcon } from 'lucide-react';


type TrendType = 'positive' | 'negative' | 'neutral';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  /** CSS variable name for the icon colour, e.g. 'var(--primary)' */
  iconColor?: string;
  trend?: string;
  trendType?: TrendType;
}

const trendStyle: Record<TrendType, { color: string; bg: string }> = {
  positive: { color: 'var(--success)',  bg: 'color-mix(in srgb, var(--success) 10%, transparent)'  },
  negative: { color: 'var(--danger)',   bg: 'color-mix(in srgb, var(--danger) 10%, transparent)'   },
  neutral:  { color: 'var(--muted)',    bg: 'color-mix(in srgb, var(--muted) 10%, transparent)'    },
};

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor = 'var(--primary)',
  trend,
  trendType = 'positive',
}: MetricCardProps) {
  const ts = trendStyle[trendType];

  return (
    <Card glow className="flex flex-col justify-between gap-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span
          className="text-[10px] font-mono-plex font-semibold uppercase tracking-widest"
          style={{ color: 'var(--muted-foreground)' }}
        >
          {title}
        </span>
        <div
          className="p-1.5 rounded-lg"
          style={{
            backgroundColor: `color-mix(in srgb, ${iconColor} 12%, transparent)`,
            border: `1px solid color-mix(in srgb, ${iconColor} 20%, transparent)`,
          }}
        >
          <Icon className="h-3.5 w-3.5" style={{ color: iconColor }} />
        </div>
      </div>

      {/* Value */}
      <div>
        <div
          className="text-xl font-brand font-700 tracking-tight"
          style={{ color: 'var(--foreground)', fontWeight: 700 }}
        >
          {value}
        </div>

        {subtitle && (
          <p className="mt-0.5 text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>
            {subtitle}
          </p>
        )}

        {trend && (
          <span
            className="inline-block mt-2 text-[11px] font-mono-plex font-semibold px-2 py-0.5 rounded-md border"
            style={{
              color: ts.color,
              backgroundColor: ts.bg,
              borderColor: `color-mix(in srgb, ${ts.color} 30%, transparent)`,
            }}
          >
            {trend}
          </span>
        )}
      </div>
    </Card>
  );
}
