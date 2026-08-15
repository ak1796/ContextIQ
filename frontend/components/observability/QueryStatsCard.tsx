/**
 * QueryStatsCard — Phase 8
 * Shows total / successful / blocked / insufficient-context query counts.
 */

import React from 'react';
import { AnalyticsSummary } from '@/lib/analytics';
import { BarChart3 } from 'lucide-react';

interface Props {
  summary: AnalyticsSummary | null;
  loading: boolean;
}

interface StatCellProps {
  label: string;
  value: number | string;
  color?: string;
}

function StatCell({ label, value, color }: StatCellProps) {
  return (
    <div className="card-elevated text-center space-y-1">
      <p
        className="text-xl font-mono-plex font-semibold"
        style={{ color: color ?? 'var(--foreground)' }}
      >
        {value}
      </p>
      <p className="text-[11px] font-sans-plex leading-tight" style={{ color: 'var(--muted)' }}>
        {label}
      </p>
    </div>
  );
}

export function QueryStatsCard({ summary, loading }: Props) {
  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-4 w-4" style={{ color: 'var(--primary)' }} aria-hidden="true" />
        <h3 className="text-sm font-brand font-semibold" style={{ color: 'var(--foreground)' }}>
          Query Overview
        </h3>
      </div>

      {loading ? (
        <p className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>Loading…</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCell
            label="Total Queries"
            value={summary?.total_queries ?? 0}
            color="var(--foreground)"
          />
          <StatCell
            label="Successful"
            value={summary?.successful_queries ?? 0}
            color="var(--success)"
          />
          <StatCell
            label="Blocked"
            value={summary?.blocked_queries ?? 0}
            color="var(--danger)"
          />
          <StatCell
            label="No Context"
            value={summary?.insufficient_context_queries ?? 0}
            color="var(--warning)"
          />
        </div>
      )}

      {/* RAG Quality sub-row */}
      {!loading && summary && summary.total_queries > 0 && (
        <div className="grid grid-cols-3 gap-3 pt-1">
          <StatCell
            label="Avg Grounding"
            value={`${(summary.average_grounding_score * 100).toFixed(1)}%`}
            color="var(--phase-output)"
          />
          <StatCell
            label="Grounded %"
            value={`${summary.grounded_response_pct.toFixed(1)}%`}
            color="var(--phase-output)"
          />
          <StatCell
            label="Tokens Saved"
            value={summary.total_tokens_saved.toLocaleString()}
            color="var(--phase-budget)"
          />
        </div>
      )}
    </div>
  );
}
