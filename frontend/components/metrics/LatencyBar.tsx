import React from 'react';
import { Card } from '@/components/ui/Card';
import { formatMs } from '@/lib/utils';
import { Clock } from 'lucide-react';

interface LatencyBarProps {
  inputGuardMs?:  number;
  retrievalMs?:   number;
  rerankMs?:      number;
  budgetMs?:      number;
  generationMs?:  number;
  outputGuardMs?: number;
  totalMs?:       number;
}

interface Segment {
  label: string;
  ms: number;
  cssVar: string;
}

export function LatencyBar({
  inputGuardMs  = 0,
  retrievalMs   = 0,
  rerankMs      = 0,
  budgetMs      = 0,
  generationMs  = 0,
  outputGuardMs = 0,
  totalMs       = 1,
}: LatencyBarProps) {
  const safeTotal = totalMs > 0 ? totalMs : 1;

  const segments: Segment[] = [
    { label: 'Input Guard',   ms: inputGuardMs,  cssVar: 'var(--phase-guard)'      },
    { label: 'Retrieval P2',  ms: retrievalMs,   cssVar: 'var(--phase-retrieval)'  },
    { label: 'Rerank P3',     ms: rerankMs,      cssVar: 'var(--phase-rerank)'     },
    { label: 'Budget P4',     ms: budgetMs,      cssVar: 'var(--phase-budget)'     },
    { label: 'Groq Gen P4',   ms: generationMs,  cssVar: 'var(--phase-generation)' },
    { label: 'Output Guard',  ms: outputGuardMs, cssVar: 'var(--phase-output)'     },
  ];

  return (
    <Card className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4" style={{ color: 'var(--primary)' }} />
          <h3
            className="text-sm font-brand font-semibold"
            style={{ color: 'var(--foreground)' }}
          >
            Pipeline Latency Breakdown
          </h3>
        </div>
        <span
          className="text-sm font-mono-plex font-semibold px-2.5 py-1 rounded-md"
          style={{
            color: 'var(--foreground)',
            backgroundColor: 'var(--surface-elevated)',
            border: '1px solid var(--border)',
          }}
        >
          {formatMs(totalMs)}
        </span>
      </div>

      {/* Multi-segment bar */}
      <div
        className="h-2.5 w-full rounded-full overflow-hidden flex"
        style={{ backgroundColor: 'var(--surface-muted)', border: '1px solid var(--border-subtle)' }}
      >
        {segments.map((seg, idx) => {
          if (seg.ms <= 0) return null;
          const pct = Math.max(1, (seg.ms / safeTotal) * 100);
          return (
            <div
              key={idx}
              style={{
                width: `${pct}%`,
                backgroundColor: seg.cssVar,
                transition: 'width 0.3s ease',
              }}
              title={`${seg.label}: ${formatMs(seg.ms)} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div
        className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-[11px] font-mono-plex pt-2"
        style={{ borderTop: '1px solid var(--border-subtle)' }}
      >
        {segments.map((seg, idx) => (
          <div key={idx} className="flex items-center gap-1.5">
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: seg.cssVar }}
            />
            <span style={{ color: 'var(--muted)' }}>{seg.label}:</span>
            <span style={{ color: seg.cssVar, fontWeight: 600 }}>{formatMs(seg.ms)}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
