/**
 * LatencyStatsCard — Phase 8
 * Displays average pipeline latency breakdown as proportional bars.
 * No chart library — pure CSS inline bars using existing design tokens.
 */

import React from 'react';
import { AnalyticsSummary } from '@/lib/analytics';
import { Clock } from 'lucide-react';

interface Props {
  summary: AnalyticsSummary | null;
  loading: boolean;
}

interface BarRowProps {
  label: string;
  value: number;
  max: number;
  color: string;
}

function BarRow({ label, value, max, color }: BarRowProps) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-sans-plex" style={{ color: 'var(--muted)' }}>
          {label}
        </span>
        <span className="text-[11px] font-mono-plex" style={{ color: 'var(--foreground)' }}>
          {value > 0 ? `${value.toFixed(0)} ms` : '—'}
        </span>
      </div>
      <div
        className="h-1.5 rounded-full overflow-hidden"
        style={{ backgroundColor: 'var(--surface-muted)' }}
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export function LatencyStatsCard({ summary, loading }: Props) {
  const total = summary?.average_latency_ms ?? 0;
  const retrieval = summary?.average_retrieval_latency_ms ?? 0;
  const rerank = summary?.average_rerank_latency_ms ?? 0;
  const generation = summary?.average_generation_latency_ms ?? 0;
  const maxBar = Math.max(total, 1);

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4" style={{ color: 'var(--primary)' }} aria-hidden="true" />
          <h3 className="text-sm font-brand font-semibold" style={{ color: 'var(--foreground)' }}>
            Avg Pipeline Latency
          </h3>
        </div>
        {total > 0 && (
          <span className="text-sm font-mono-plex font-semibold" style={{ color: 'var(--phase-generation)' }}>
            {total.toFixed(0)} ms
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>Loading…</p>
      ) : total === 0 ? (
        <p className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>
          No query data yet. Run a query to populate latency metrics.
        </p>
      ) : (
        <div className="space-y-3">
          <BarRow label="Total" value={total} max={maxBar} color="var(--phase-generation)" />
          <BarRow label="Retrieval" value={retrieval} max={maxBar} color="var(--phase-retrieval)" />
          <BarRow label="Reranking" value={rerank} max={maxBar} color="var(--phase-rerank)" />
          <BarRow label="Generation" value={generation} max={maxBar} color="var(--phase-budget)" />
        </div>
      )}

      {/* Compression ratio row */}
      {!loading && summary && summary.total_queries > 0 && (
        <div
          className="flex items-center justify-between pt-2"
          style={{ borderTop: '1px solid var(--border-subtle)' }}
        >
          <span className="text-[11px] font-sans-plex" style={{ color: 'var(--muted)' }}>
            Avg Compression Ratio
          </span>
          <span className="text-[11px] font-mono-plex" style={{ color: 'var(--phase-budget)' }}>
            {(summary.average_compression_ratio * 100).toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}
