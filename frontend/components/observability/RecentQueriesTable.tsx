/**
 * RecentQueriesTable — Phase 8
 * Compact table of recent query records (metadata only — no question text).
 * Bounded display, responsive, uses existing design system.
 */

import React from 'react';
import { RecentQueryRecord } from '@/lib/analytics';
import { List } from 'lucide-react';

interface Props {
  queries: RecentQueryRecord[];
  loading: boolean;
}

function statusBadgeStyle(status: string): React.CSSProperties {
  switch (status) {
    case 'grounded':
    case 'partially_grounded':
      return { backgroundColor: 'color-mix(in srgb, var(--success) 12%, transparent)', color: 'var(--success)', border: '1px solid color-mix(in srgb, var(--success) 30%, transparent)' };
    case 'blocked':
      return { backgroundColor: 'color-mix(in srgb, var(--danger) 12%, transparent)', color: 'var(--danger)', border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)' };
    case 'insufficient_context':
      return { backgroundColor: 'color-mix(in srgb, var(--warning) 12%, transparent)', color: 'var(--warning)', border: '1px solid color-mix(in srgb, var(--warning) 30%, transparent)' };
    default:
      return { backgroundColor: 'color-mix(in srgb, var(--muted) 12%, transparent)', color: 'var(--muted)', border: '1px solid color-mix(in srgb, var(--muted) 25%, transparent)' };
  }
}

function formatTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return isoString;
  }
}

export function RecentQueriesTable({ queries, loading }: Props) {
  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <List className="h-4 w-4" style={{ color: 'var(--primary)' }} aria-hidden="true" />
          <h3 className="text-sm font-brand font-semibold" style={{ color: 'var(--foreground)' }}>
            Recent Queries
          </h3>
        </div>
        {queries.length > 0 && (
          <span className="text-[11px] font-mono-plex" style={{ color: 'var(--muted)' }}>
            {queries.length} record{queries.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>Loading…</p>
      ) : queries.length === 0 ? (
        <p className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>
          No queries recorded yet. Run a query in the Query Bench tab to populate this table.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Time', 'Document', 'Status', 'Grounding', 'Latency', 'Tokens Saved'].map((h) => (
                  <th
                    key={h}
                    className="pb-2 text-left font-sans-plex font-medium"
                    style={{ color: 'var(--muted)', paddingRight: '1rem', whiteSpace: 'nowrap' }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {queries.map((q, idx) => (
                <tr
                  key={idx}
                  style={{ borderBottom: '1px solid var(--border-subtle)' }}
                >
                  <td className="py-2 font-mono-plex" style={{ color: 'var(--muted)', paddingRight: '1rem', whiteSpace: 'nowrap' }}>
                    {formatTime(q.timestamp)}
                  </td>
                  <td className="py-2 font-mono-plex" style={{ color: 'var(--foreground)', paddingRight: '1rem', maxWidth: '10rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {q.doc_id || '—'}
                  </td>
                  <td className="py-2" style={{ paddingRight: '1rem' }}>
                    <span
                      className="badge-base"
                      style={statusBadgeStyle(q.answer_status)}
                    >
                      {q.answer_status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="py-2 font-mono-plex" style={{ color: 'var(--phase-output)', paddingRight: '1rem', whiteSpace: 'nowrap' }}>
                    {q.grounding_score != null ? `${(q.grounding_score * 100).toFixed(0)}%` : '—'}
                  </td>
                  <td className="py-2 font-mono-plex" style={{ color: 'var(--phase-retrieval)', paddingRight: '1rem', whiteSpace: 'nowrap' }}>
                    {q.total_latency_ms > 0 ? `${q.total_latency_ms.toFixed(0)} ms` : '—'}
                  </td>
                  <td className="py-2 font-mono-plex" style={{ color: 'var(--phase-budget)', whiteSpace: 'nowrap' }}>
                    {q.tokens_saved > 0 ? q.tokens_saved.toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
