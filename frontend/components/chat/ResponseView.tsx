import React from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { QueryResponse } from '@/lib/types';
import { getStatusBadgeVariant, formatPercentage } from '@/lib/utils';
import { ShieldCheck, ShieldAlert, AlertTriangle, Cpu } from 'lucide-react';

interface ResponseViewProps {
  data: QueryResponse;
}

export function ResponseView({ data }: ResponseViewProps) {
  const { variant, label } = getStatusBadgeVariant(data.answer_status);
  const isBlocked     = data.answer_status === 'blocked' || !data.success;
  const isInsufficient = data.answer_status === 'insufficient_context';

  /* Colour token used for answer-box border/bg */
  const answerAccent = isBlocked
    ? 'var(--danger)'
    : isInsufficient
    ? 'var(--info)'
    : 'var(--border)';

  return (
    <Card glow className="space-y-4">
      {/* Status bar */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 pb-3"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2">
          <Badge variant={variant}>
            {isBlocked
              ? <ShieldAlert className="h-3.5 w-3.5" />
              : isInsufficient
              ? <AlertTriangle className="h-3.5 w-3.5" />
              : <ShieldCheck className="h-3.5 w-3.5" />
            }
            <span className="font-sans-plex">{label}</span>
          </Badge>

          {/* Risk level chip */}
          <span
            className="text-xs px-2 py-0.5 rounded font-mono-plex font-semibold border"
            style={{
              color: data.risk_level === 'high'
                ? 'var(--danger)'
                : data.risk_level === 'medium'
                ? 'var(--warning)'
                : 'var(--success)',
              backgroundColor: `color-mix(in srgb, ${
                data.risk_level === 'high'
                  ? 'var(--danger)'
                  : data.risk_level === 'medium'
                  ? 'var(--warning)'
                  : 'var(--success)'
              } 10%, transparent)`,
              borderColor: `color-mix(in srgb, ${
                data.risk_level === 'high'
                  ? 'var(--danger)'
                  : data.risk_level === 'medium'
                  ? 'var(--warning)'
                  : 'var(--success)'
              } 25%, transparent)`,
            }}
          >
            Risk: {(data.risk_level ?? 'low').toUpperCase()}
          </span>
        </div>

        {/* Model + version */}
        <div
          className="flex items-center gap-2 text-xs font-mono-plex"
          style={{ color: 'var(--muted)' }}
        >
          <Cpu className="h-3.5 w-3.5" style={{ color: 'var(--primary)' }} />
          <span>{data.model}</span>
          <span style={{ color: 'var(--border)' }}>•</span>
          <span>v{data.doc_version}</span>
        </div>
      </div>

      {/* Answer section */}
      <div className="space-y-1.5">
        <span
          className="text-[10px] font-mono-plex font-semibold uppercase tracking-widest"
          style={{ color: 'var(--muted-foreground)' }}
        >
          Generated Answer
        </span>
        <div
          className="p-4 rounded-xl text-sm leading-relaxed font-sans-plex"
          style={{
            backgroundColor: `color-mix(in srgb, ${answerAccent} 5%, var(--surface-muted))`,
            border: `1px solid color-mix(in srgb, ${answerAccent} 30%, var(--border-subtle))`,
            color: 'var(--foreground)',
          }}
        >
          {data.answer}
        </div>
      </div>

      {/* Guardrail block reason */}
      {data.reason && isBlocked && (
        <div
          className="p-3 rounded-lg flex items-start gap-2 text-xs font-sans-plex"
          style={{
            backgroundColor: `color-mix(in srgb, var(--danger) 8%, transparent)`,
            border: `1px solid color-mix(in srgb, var(--danger) 25%, transparent)`,
            color: 'var(--danger)',
          }}
        >
          <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block">Guardrail Block Reason:</span>
            <span>{data.reason}</span>
          </div>
        </div>
      )}

      {/* Unsupported claims */}
      {data.unsupported_claims && data.unsupported_claims.length > 0 && !isBlocked && (
        <div
          className="p-3 rounded-lg text-xs font-sans-plex space-y-1"
          style={{
            backgroundColor: `color-mix(in srgb, var(--warning) 8%, transparent)`,
            border: `1px solid color-mix(in srgb, var(--warning) 25%, transparent)`,
            color: 'var(--warning)',
          }}
        >
          <div className="flex items-center gap-1.5 font-semibold">
            <AlertTriangle className="h-3.5 w-3.5" />
            Unsupported Statements ({data.unsupported_claims.length}):
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px]" style={{ color: 'var(--foreground)' }}>
            {data.unsupported_claims.map((claim, idx) => (
              <li key={idx} className="truncate">{claim}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer metric row */}
      {!isBlocked && (
        <div
          className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3"
          style={{ borderTop: '1px solid var(--border-subtle)' }}
        >
          {[
            { label: 'Grounding', value: formatPercentage(data.grounding_score), color: 'var(--success)' },
            { label: 'Tokens Saved', value: `${data.tokens_saved}`, color: 'var(--primary)' },
            { label: 'Chunks', value: `${data.selected_chunks_count}/${data.retrieved_chunks}`, color: 'var(--phase-rerank)' },
            { label: 'Latency', value: `${data.total_latency_ms.toFixed(0)} ms`, color: 'var(--phase-retrieval)' },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="p-2 rounded-lg"
              style={{ backgroundColor: 'var(--surface-muted)', border: '1px solid var(--border-subtle)' }}
            >
              <span className="text-[10px] font-mono-plex block" style={{ color: 'var(--muted-foreground)' }}>{label}</span>
              <span className="text-sm font-brand font-semibold" style={{ color }}>{value}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
