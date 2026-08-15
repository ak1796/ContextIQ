import React from 'react';
import { Card } from '@/components/ui/Card';
import { Zap, Database, ArrowRight } from 'lucide-react';

interface ContextEfficiencyCardProps {
  originalTokens?: number;
  compressedTokens?: number;
  tokensSaved?: number;
  compressionRatio?: number;
  retrievedChunks?: number;
  rerankedChunks?: number;
  selectedChunks?: number;
}

export function ContextEfficiencyCard({
  originalTokens = 0,
  compressedTokens = 0,
  tokensSaved = 0,
  compressionRatio = 1.0,
  retrievedChunks = 0,
  rerankedChunks = 0,
  selectedChunks = 0,
}: ContextEfficiencyCardProps) {
  const reductionPct = ((1 - compressionRatio) * 100).toFixed(1);

  return (
    <Card glow className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between pb-3 border-b border-[color:var(--border-subtle)]">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-[color:var(--phase-budget)]" />
          <h3 className="text-sm font-brand font-semibold text-[color:var(--foreground)]">
            Context & Token Efficiency Metrics
          </h3>
        </div>
        <span
          className="text-xs font-mono-plex font-semibold px-2.5 py-0.5 rounded border"
          style={{
            color: 'var(--success)',
            backgroundColor: 'color-mix(in srgb, var(--success) 10%, transparent)',
            borderColor: 'color-mix(in srgb, var(--success) 25%, transparent)',
          }}
        >
          {reductionPct}% Token Reduction
        </span>
      </div>

      {/* Row 1: Token Counts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div
          className="p-3 rounded-lg space-y-1"
          style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border-subtle)' }}
        >
          <span className="text-[10px] font-mono-plex font-semibold uppercase tracking-wider text-[color:var(--muted-foreground)] block">
            Original Context Tokens
          </span>
          <span className="text-lg font-mono-plex font-bold text-[color:var(--foreground)] block">
            {originalTokens}
          </span>
        </div>

        <div
          className="p-3 rounded-lg space-y-1"
          style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border-subtle)' }}
        >
          <span className="text-[10px] font-mono-plex font-semibold uppercase tracking-wider text-[color:var(--muted-foreground)] block">
            Compressed Tokens
          </span>
          <span className="text-lg font-mono-plex font-bold text-[color:var(--primary)] block">
            {compressedTokens}
          </span>
        </div>

        <div
          className="p-3 rounded-lg space-y-1"
          style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border-subtle)' }}
        >
          <span className="text-[10px] font-mono-plex font-semibold uppercase tracking-wider text-[color:var(--muted-foreground)] block">
            Net Tokens Saved
          </span>
          <span className="text-lg font-mono-plex font-bold text-[color:var(--success)] block">
            +{tokensSaved}
          </span>
        </div>

        <div
          className="p-3 rounded-lg space-y-1"
          style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border-subtle)' }}
        >
          <span className="text-[10px] font-mono-plex font-semibold uppercase tracking-wider text-[color:var(--muted-foreground)] block">
            Compression Ratio
          </span>
          <span className="text-lg font-mono-plex font-bold text-[color:var(--phase-rerank)] block">
            {compressionRatio.toFixed(3)}
          </span>
        </div>
      </div>

      {/* Row 2: Candidate Funnel (Retrieved -> Reranked -> Selected) */}
      <div
        className="p-3.5 rounded-lg space-y-2"
        style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2">
          <Database className="h-3.5 w-3.5 text-[color:var(--phase-retrieval)]" />
          <span className="text-xs font-sans-plex font-semibold text-[color:var(--foreground)]">
            Context Candidate Funnel
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono-plex pt-1">
          <div className="flex items-center gap-2">
            <span className="text-[color:var(--muted)]">Retrieved:</span>
            <span className="font-bold text-[color:var(--phase-retrieval)] px-2 py-0.5 rounded bg-[color:var(--surface-muted)]">
              {retrievedChunks}
            </span>
          </div>

          <ArrowRight className="h-3.5 w-3.5 text-[color:var(--muted-foreground)] hidden sm:inline" />

          <div className="flex items-center gap-2">
            <span className="text-[color:var(--muted)]">Reranked:</span>
            <span className="font-bold text-[color:var(--phase-rerank)] px-2 py-0.5 rounded bg-[color:var(--surface-muted)]">
              {rerankedChunks}
            </span>
          </div>

          <ArrowRight className="h-3.5 w-3.5 text-[color:var(--muted-foreground)] hidden sm:inline" />

          <div className="flex items-center gap-2">
            <span className="text-[color:var(--muted)]">Selected:</span>
            <span className="font-bold text-[color:var(--primary)] px-2 py-0.5 rounded bg-[color:var(--surface-muted)]">
              {selectedChunks}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}
