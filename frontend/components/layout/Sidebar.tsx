'use client';

import React from 'react';
import { Terminal, BarChart2, ShieldCheck, Database, Layers, ExternalLink, FileText, UploadCloud } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getApiBaseUrl } from '@/lib/api';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  selectedDocId?: string;
  onSelectDocId?: (docId: string) => void;
}

const NAV_ITEMS = [
  { id: 'query',       label: 'Query Bench',     icon: Terminal    },
  { id: 'documents',   label: 'Document Ingest', icon: UploadCloud   },
  { id: 'analytics',  label: 'Token Analytics',  icon: BarChart2   },
  { id: 'guardrails', label: 'Guardrail Audit',  icon: ShieldCheck },
  { id: 'vectorstore',label: 'Vector Index',     icon: Database    },
];

const PIPELINE_STAGES = [
  { label: 'P1 Compress:', value: 'LLMLingua-2',   phase: 'generation' },
  { label: 'P1 Cache:',    value: 'Redis/SQLite',   phase: 'output'     },
  { label: 'P2 Embed:',    value: 'MiniLM-L6-v2',  phase: 'retrieval'  },
  { label: 'P3 Rerank:',   value: 'ms-marco',       phase: 'rerank'     },
  { label: 'P4 Budget:',   value: 'Dynamic Context', phase: 'budget'     },
  { label: 'P4 Gen:',      value: 'Groq LLM',       phase: 'guard'      },
  { label: 'P5 Safety:',   value: 'Sent. Grounding',phase: 'output'     },
];

export function Sidebar({ activeTab, setActiveTab, selectedDocId, onSelectDocId }: SidebarProps) {
  const docsUrl = `${getApiBaseUrl()}/docs`;

  return (
    <aside
      style={{
        borderRight: '1px solid var(--border)',
        backgroundColor: 'var(--surface)',
      }}
      className="w-60 p-4 flex flex-col justify-between hidden md:flex min-h-[calc(100vh-57px)] shrink-0"
    >
      <div className="space-y-5">
        {/* Nav label */}
        <p
          className="px-2 text-[10px] font-mono-plex font-semibold uppercase tracking-widest"
          style={{ color: 'var(--muted-foreground)' }}
        >
          Navigation
        </p>

        {/* Nav items */}
        <nav className="space-y-0.5">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
            const isActive = activeTab === id;
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                style={
                  isActive
                    ? {
                        backgroundColor: `color-mix(in srgb, var(--primary) 10%, transparent)`,
                        color: 'var(--primary)',
                        border: `1px solid color-mix(in srgb, var(--primary) 25%, transparent)`,
                      }
                    : {
                        color: 'var(--muted)',
                        border: '1px solid transparent',
                      }
                }
                className={cn(
                  'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-sans-plex font-medium transition-all duration-100',
                  !isActive && 'hover:text-[color:var(--foreground)] hover:bg-[color:var(--surface-muted)]'
                )}
              >
                <Icon
                  className="h-4 w-4 shrink-0"
                  style={{ color: isActive ? 'var(--primary)' : 'var(--muted-foreground)' }}
                />
                {label}
              </button>
            );
          })}
        </nav>

        {/* Document Target Input in Sidebar */}
        {onSelectDocId && (
          <div className="px-2 space-y-1.5">
            <label
              htmlFor="sidebar-doc-input"
              className="text-[10px] font-mono-plex font-semibold uppercase tracking-widest block"
              style={{ color: 'var(--muted-foreground)' }}
            >
              Target Document ID
            </label>
            <div className="relative flex items-center">
              <FileText className="h-3.5 w-3.5 absolute left-2.5" style={{ color: 'var(--primary)' }} />
              <input
                id="sidebar-doc-input"
                type="text"
                value={selectedDocId || 'doc1.txt'}
                onChange={(e) => onSelectDocId(e.target.value)}
                placeholder="e.g. doc1.txt"
                className="w-full text-xs font-mono-plex pl-8 pr-2 py-1.5 rounded-lg border outline-none transition-all"
                style={{
                  backgroundColor: 'var(--surface-elevated)',
                  borderColor: 'var(--border)',
                  color: 'var(--foreground)',
                }}
              />
            </div>
          </div>
        )}

        {/* Pipeline summary card */}
        <div
          className="rounded-xl p-3 space-y-2"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div className="flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5" style={{ color: 'var(--phase-retrieval)' }} />
            <span
              className="text-xs font-sans-plex font-semibold"
              style={{ color: 'var(--foreground)' }}
            >
              Pipeline Architecture
            </span>
          </div>
          <ul className="space-y-1.5">
            {PIPELINE_STAGES.map(({ label, value, phase }) => (
              <li key={label} className="flex items-center justify-between text-[11px] font-mono-plex">
                <span style={{ color: 'var(--muted)' }}>{label}</span>
                <span
                  style={{ color: `var(--phase-${phase})`, fontWeight: 600 }}
                >
                  {value}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Footer link */}
      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
        <a
          href={docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-sans-plex transition-colors"
          style={{ color: 'var(--muted)' }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.color = 'var(--foreground)';
            (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--surface-muted)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.color = 'var(--muted)';
            (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
          }}
        >
          <span>FastAPI OpenAPI Specs</span>
          <ExternalLink className="h-3.5 w-3.5" style={{ color: 'var(--muted-foreground)' }} />
        </a>
      </div>
    </aside>
  );
}
