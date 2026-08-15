/**
 * ObservabilityDashboard — Phase 8
 *
 * Production observability view: system health, query overview, RAG quality,
 * performance metrics, and recent query history.
 *
 * Fetches data on mount and auto-refreshes every 30 seconds.
 * Uses only the existing Phase 6 design system — no new fonts or colors.
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import {
  fetchSystemHealth,
  fetchAnalyticsSummary,
  fetchRecentQueries,
  SystemHealth,
  AnalyticsSummary,
  RecentQueryRecord,
} from '@/lib/analytics';
import { SystemHealthCard } from './SystemHealthCard';
import { QueryStatsCard } from './QueryStatsCard';
import { LatencyStatsCard } from './LatencyStatsCard';
import { RecentQueriesTable } from './RecentQueriesTable';

const REFRESH_INTERVAL_MS = 30_000;

async function loadObservabilityData() {
  return Promise.allSettled([
    fetchSystemHealth(),
    fetchAnalyticsSummary(),
    fetchRecentQueries(50),
  ]);
}

export function ObservabilityDashboard() {
  const [health, setHealth]           = useState<SystemHealth | null>(null);
  const [summary, setSummary]         = useState<AnalyticsSummary | null>(null);
  const [recent, setRecent]           = useState<RecentQueryRecord[]>([]);
  const [loadingH, setLoadingH]       = useState(true);
  const [loadingS, setLoadingS]       = useState(true);
  const [loadingR, setLoadingR]       = useState(true);
  const [errorH, setErrorH]           = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const applyResults = useCallback(
    (results: PromiseSettledResult<unknown>[]) => {
      const [h, s, r] = results;

      if (h.status === 'fulfilled') {
        setHealth(h.value as SystemHealth);
        setErrorH(null);
      } else {
        setHealth(null);
        setErrorH('Could not reach backend. Ensure FastAPI is running.');
      }
      setLoadingH(false);

      if (s.status === 'fulfilled') setSummary(s.value as AnalyticsSummary);
      setLoadingS(false);

      if (r.status === 'fulfilled') setRecent(r.value as RecentQueryRecord[]);
      setLoadingR(false);

      setLastRefresh(new Date());
    },
    [],
  );

  const refresh = useCallback(() => {
    setLoadingH(true);
    setLoadingS(true);
    setLoadingR(true);
    loadObservabilityData().then(applyResults).catch(() => {
      setLoadingH(false);
      setLoadingS(false);
      setLoadingR(false);
    });
  }, [applyResults]);

  // Fetch on mount — async IIFE so setState is called inside a Promise callback,
  // not synchronously in the effect body (satisfies react-hooks/set-state-in-effect).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const results = await loadObservabilityData();
      if (!cancelled) applyResults(results);
    })();
    return () => { cancelled = true; };
  }, [applyResults]);

  // Auto-refresh every 30s
  useEffect(() => {
    const id = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-brand font-semibold" style={{ color: 'var(--foreground)' }}>
            Observability Dashboard
          </h2>
          <p className="text-xs font-sans-plex mt-0.5" style={{ color: 'var(--muted)' }}>
            Live system health &amp; query analytics — auto-refreshes every 30 s
          </p>
        </div>
        <button
          id="observability-refresh-btn"
          onClick={refresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-sans-plex transition-colors"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--muted)',
            cursor: 'pointer',
          }}
          aria-label="Refresh observability data"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Last refresh timestamp */}
      {lastRefresh && (
        <p className="text-[11px] font-mono-plex -mt-4" style={{ color: 'var(--muted-foreground)' }}>
          Last updated: {lastRefresh.toLocaleTimeString()}
        </p>
      )}

      {/* Row 1: System Health + Query Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SystemHealthCard health={health} loading={loadingH} error={errorH} />
        <QueryStatsCard summary={summary} loading={loadingS} />
      </div>

      {/* Row 2: Latency Breakdown */}
      <LatencyStatsCard summary={summary} loading={loadingS} />

      {/* Row 3: Recent Queries */}
      <RecentQueriesTable queries={recent} loading={loadingR} />
    </div>
  );
}
