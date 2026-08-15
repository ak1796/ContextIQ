/**
 * SystemHealthCard — Phase 8
 * Displays service status for Backend, Redis, Vector Store, LLM, and document count.
 * Uses only existing semantic CSS variables — no new colors.
 */

import React from 'react';
import { SystemHealth } from '@/lib/analytics';
import { CheckCircle, XCircle, AlertCircle, Server } from 'lucide-react';

interface Props {
  health: SystemHealth | null;
  loading: boolean;
  error: string | null;
}

interface StatusRowProps {
  label: string;
  value: string;
  ok: boolean;
  warn?: boolean;
}

function StatusDot({ ok, warn }: { ok: boolean; warn?: boolean }) {
  const color = ok ? 'var(--success)' : warn ? 'var(--warning)' : 'var(--danger)';
  const Icon = ok ? CheckCircle : warn ? AlertCircle : XCircle;
  return <Icon className="h-4 w-4 shrink-0" style={{ color }} aria-hidden="true" />;
}

function StatusRow({ label, value, ok, warn }: StatusRowProps) {
  return (
    <div className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <span className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>{label}</span>
      <div className="flex items-center gap-2">
        <StatusDot ok={ok} warn={warn} />
        <span className="text-xs font-mono-plex" style={{ color: ok ? 'var(--success)' : warn ? 'var(--warning)' : 'var(--danger)' }}>
          {value}
        </span>
      </div>
    </div>
  );
}

export function SystemHealthCard({ health, loading, error }: Props) {
  if (loading) {
    return (
      <div className="card space-y-3">
        <h3 className="text-sm font-brand font-semibold" style={{ color: 'var(--foreground)' }}>
          System Health
        </h3>
        <p className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>Checking services…</p>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="card space-y-3">
        <h3 className="text-sm font-brand font-semibold" style={{ color: 'var(--foreground)' }}>
          System Health
        </h3>
        <p className="text-xs font-sans-plex" style={{ color: 'var(--danger)' }}>
          {error ?? 'Health data unavailable'}
        </p>
      </div>
    );
  }

  const isHealthy = health.status === 'healthy';

  return (
    <div className="card space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4" style={{ color: 'var(--primary)' }} aria-hidden="true" />
          <h3 className="text-sm font-brand font-semibold" style={{ color: 'var(--foreground)' }}>
            System Health
          </h3>
        </div>
        <span
          className="badge-base"
          style={{
            backgroundColor: isHealthy ? 'color-mix(in srgb, var(--success) 12%, transparent)' : 'color-mix(in srgb, var(--warning) 12%, transparent)',
            color: isHealthy ? 'var(--success)' : 'var(--warning)',
            border: `1px solid ${isHealthy ? 'color-mix(in srgb, var(--success) 30%, transparent)' : 'color-mix(in srgb, var(--warning) 30%, transparent)'}`,
          }}
        >
          {health.status.toUpperCase()}
        </span>
      </div>

      {/* Status rows */}
      <div>
        <StatusRow label="Backend API" value="running" ok={true} />
        <StatusRow
          label="Redis Cache"
          value={health.redis}
          ok={health.redis === 'connected'}
          warn={false}
        />
        <StatusRow
          label="Vector Store"
          value={health.vector_store}
          ok={health.vector_store === 'healthy'}
        />
        <StatusRow
          label="LLM (Groq)"
          value={health.llm}
          ok={health.llm === 'available'}
          warn={health.llm === 'unconfigured'}
        />
        <div className="flex items-center justify-between py-2">
          <span className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>Documents</span>
          <span className="text-xs font-mono-plex" style={{ color: 'var(--foreground)' }}>
            {health.documents}
          </span>
        </div>
      </div>

      <p className="text-[10px] font-mono-plex" style={{ color: 'var(--muted-foreground)' }}>
        Last checked: {new Date(health.timestamp).toLocaleTimeString()}
      </p>
    </div>
  );
}
