import React from 'react';
import { Card } from '@/components/ui/Card';
import { Database, Cpu, Layers, HardDrive } from 'lucide-react';

interface DocumentInfoCardProps {
  docId?: string;
  docVersion?: number;
  model?: string;
}

export function DocumentInfoCard({
  docId = 'doc1.txt',
  docVersion = 1,
  model = 'llama-3.3-70b-versatile',
}: DocumentInfoCardProps) {
  const items = [
    { label: 'Target Document ID', value: docId, icon: Database, color: 'var(--primary)' },
    { label: 'Document Version', value: `v${docVersion}`, icon: Layers, color: 'var(--phase-budget)' },
    { label: 'Cache Backend', value: 'Redis / SQLite', icon: HardDrive, color: 'var(--phase-output)' },
    { label: 'Embedding Model', value: 'all-MiniLM-L6-v2 (384-dim)', icon: Cpu, color: 'var(--phase-retrieval)' },
    { label: 'Cross-Encoder Reranker', value: 'ms-marco-MiniLM-L-6-v2', icon: Layers, color: 'var(--phase-rerank)' },
    { label: 'Groq LLM Generation', value: model, icon: Cpu, color: 'var(--phase-generation)' },
  ];

  return (
    <Card glow className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-2 pb-3 border-b border-[color:var(--border-subtle)]">
        <Database className="h-4 w-4 text-[color:var(--primary)]" />
        <h3 className="text-sm font-brand font-semibold text-[color:var(--foreground)]">
          Document & System Environment Metadata
        </h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {items.map(({ label, value, icon: Icon, color }) => (
          <div
            key={label}
            className="p-3 rounded-lg flex items-start gap-2.5"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div
              className="p-1.5 rounded-md shrink-0 mt-0.5"
              style={{
                backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`,
                border: `1px solid color-mix(in srgb, ${color} 20%, transparent)`,
              }}
            >
              <Icon className="h-3.5 w-3.5" style={{ color }} />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-[10px] font-mono-plex uppercase tracking-wider text-[color:var(--muted-foreground)] block">
                {label}
              </span>
              <span className="text-xs font-mono-plex font-semibold text-[color:var(--foreground)] truncate block mt-0.5">
                {value}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
