'use client';

import React, { useEffect, useState } from 'react';
import { Cpu, Activity, Database, Sparkles } from 'lucide-react';
import { checkHealth } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';

interface HeaderProps {
  activeModel?: string;
}

export function Header({ activeModel }: HeaderProps) {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    async function verifyBackend() {
      const res = await checkHealth();
      setIsOnline(res.status === 'ok');
    }
    verifyBackend();
    const interval = setInterval(verifyBackend, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header
      style={{
        backgroundColor: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}
      className="sticky top-0 z-50 backdrop-blur-xl px-6 py-3 flex items-center justify-between"
    >
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div
          style={{ backgroundColor: 'var(--primary)' }}
          className="h-9 w-9 rounded-xl flex items-center justify-center shadow-sm"
        >
          <Sparkles className="h-4 w-4" style={{ color: 'var(--primary-foreground)' }} />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1
              className="font-brand text-base font-semibold tracking-tight"
              style={{ color: 'var(--foreground)' }}
            >
              ContextIQ
            </h1>
            <span
              className="badge-base badge-primary font-mono-plex text-[10px]"
              style={{ borderRadius: '0.375rem' }}
            >
              v1.0
            </span>
          </div>
          <p className="text-xs font-sans-plex" style={{ color: 'var(--muted)' }}>
            Compressed Vector RAG &amp; Calibrated Token Budget Platform
          </p>
        </div>
      </div>

      {/* Status row */}
      <div className="flex items-center gap-3">
        <Badge variant={isOnline ? 'success' : isOnline === false ? 'danger' : 'muted'}>
          <Activity className="h-3 w-3" style={isOnline ? { animation: 'pulse 2s infinite' } : {}} />
          <span className="font-sans-plex">
            {isOnline === null ? 'Checking…' : isOnline ? 'Backend Online' : 'Backend Offline'}
          </span>
        </Badge>

        <div
          className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono-plex"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--muted)',
          }}
        >
          <Cpu className="h-3.5 w-3.5" style={{ color: 'var(--phase-rerank)' }} />
          <span>{activeModel || 'Groq Generation Engine'}</span>
          <span style={{ color: 'var(--border)' }}>•</span>
          <Database className="h-3.5 w-3.5" style={{ color: 'var(--phase-retrieval)' }} />
          <span>MiniLM-L6-v2</span>
        </div>
      </div>
    </header>
  );
}
