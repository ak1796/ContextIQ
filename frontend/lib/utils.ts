export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function formatMs(ms: number | undefined): string {
  if (ms === undefined || ms === null) return '0 ms';
  if (ms < 1) return `${(ms * 1000).toFixed(0)} µs`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
  return `${ms.toFixed(1)} ms`;
}

export function formatPercentage(val: number | undefined): string {
  if (val === undefined || val === null) return '0%';
  return `${(val * 100).toFixed(1)}%`;
}

/** Maps pipeline answer_status → semantic Badge variant */
export function getStatusBadgeVariant(status: string | undefined): {
  variant: 'success' | 'warning' | 'info' | 'danger' | 'muted';
  label: string;
} {
  switch (status) {
    case 'grounded':
      return { variant: 'success', label: 'Grounded' };
    case 'partially_grounded':
      return { variant: 'warning', label: 'Partially Grounded' };
    case 'insufficient_context':
      return { variant: 'info', label: 'Insufficient Context' };
    case 'blocked':
      return { variant: 'danger', label: 'Security Blocked' };
    default:
      return { variant: 'muted', label: status || 'Unknown' };
  }
}
