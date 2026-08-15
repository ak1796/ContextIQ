'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Chunk } from '@/lib/types';
import { Layers, ChevronDown, ChevronUp, Hash, Database, Sparkles, Filter } from 'lucide-react';

interface ChunkInspectorProps {
  selectedChunks: Chunk[];
  rerankedChunks: Chunk[];
  retrievedCandidates: Chunk[];
}

interface ChunkCardProps {
  chunk: Chunk;
  index: number;
  accentVar: string;
}

function ChunkCardItem({ chunk, index, accentVar }: ChunkCardProps) {
  const [showOriginal, setShowOriginal] = useState(false);

  return (
    <div
      className="rounded-lg p-3.5 space-y-2.5 transition-all text-xs font-sans-plex"
      style={{
        backgroundColor: 'var(--surface-elevated)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      {/* Chunk metadata row */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono-plex">
        <div className="flex items-center gap-2">
          <span
            className="px-2 py-0.5 rounded font-semibold"
            style={{
              backgroundColor: 'var(--surface-muted)',
              color: 'var(--foreground)',
              border: '1px solid var(--border)',
            }}
          >
            Index #{chunk.chunk_index ?? index}
          </span>
          <span className="flex items-center gap-1" style={{ color: 'var(--muted)' }}>
            <Hash className="h-3 w-3" style={{ color: 'var(--primary)' }} />
            {chunk.cache_key || `key_${index}`}
          </span>
          {chunk.doc_version !== undefined && (
            <span
              className="px-1.5 py-0.5 rounded text-[10px]"
              style={{ backgroundColor: 'var(--surface-muted)', color: 'var(--muted-foreground)' }}
            >
              v{chunk.doc_version}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {chunk.similarity_score !== undefined && (
            <span style={{ color: 'var(--phase-retrieval)', fontWeight: 600 }}>
              Similarity: {chunk.similarity_score.toFixed(4)}
            </span>
          )}
          {chunk.relevance_score !== undefined && (
            <span style={{ color: 'var(--phase-rerank)', fontWeight: 600 }}>
              Relevance Logit: {chunk.relevance_score}
            </span>
          )}
          {chunk.token_count_before !== undefined && chunk.token_count_after !== undefined && (
            <span style={{ color: 'var(--phase-budget)', fontWeight: 600 }}>
              Tokens: {chunk.token_count_before} → {chunk.token_count_after}
            </span>
          )}
          {chunk.original_text && (
            <button
              onClick={() => setShowOriginal(!showOriginal)}
              className="text-xs font-sans-plex font-medium underline transition-colors"
              style={{ color: 'var(--primary)' }}
              aria-label={showOriginal ? 'Hide original text' : 'Show original text'}
            >
              {showOriginal ? 'Hide Original' : 'View Original'}
            </button>
          )}
        </div>
      </div>

      {/* Compressed Text view */}
      <div>
        <span
          className="text-[10px] font-mono-plex uppercase tracking-wider font-semibold block mb-1"
          style={{ color: accentVar }}
        >
          Compressed Context:
        </span>
        <div
          className="p-2.5 rounded text-xs font-sans-plex leading-relaxed"
          style={{
            backgroundColor: 'var(--surface-muted)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--foreground)',
          }}
        >
          {chunk.compressed_text || chunk.original_text || 'No text content available.'}
        </div>
      </div>

      {/* Original Uncompressed Text (Expandable) */}
      {showOriginal && chunk.original_text && (
        <div className="pt-2 space-y-1 border-t border-[color:var(--border-subtle)] animate-fade-in">
          <span
            className="text-[10px] font-mono-plex uppercase tracking-wider font-semibold block text-[color:var(--muted-foreground)]"
          >
            Original Uncompressed Text:
          </span>
          <div
            className="p-2.5 rounded text-xs font-sans-plex leading-relaxed text-[color:var(--muted)]"
            style={{
              backgroundColor: 'var(--surface-muted)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {chunk.original_text}
          </div>
        </div>
      )}
    </div>
  );
}

interface AccordionSectionProps {
  id: string;
  title: string;
  count: number;
  icon: React.ElementType;
  accentVar: string;
  isOpen: boolean;
  onToggle: () => void;
  chunks: Chunk[];
}

function AccordionSection({
  id,
  title,
  count,
  icon: Icon,
  accentVar,
  isOpen,
  onToggle,
  chunks,
}: AccordionSectionProps) {
  return (
    <div
      className="rounded-xl overflow-hidden transition-all"
      style={{
        backgroundColor: 'var(--surface)',
        border: isOpen ? `1px solid ${accentVar}` : '1px solid var(--border)',
      }}
    >
      {/* Accordion Trigger Header */}
      <button
        onClick={onToggle}
        aria-expanded={isOpen}
        aria-controls={`section-${id}`}
        className="w-full px-4 py-3 flex items-center justify-between transition-colors hover:bg-[color:var(--surface-elevated)]"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="h-4 w-4" style={{ color: accentVar }} />
          <span className="text-xs font-brand font-semibold text-[color:var(--foreground)]">
            {title}
          </span>
          <span
            className="text-xs font-mono-plex px-2 py-0.5 rounded-full font-semibold"
            style={{
              backgroundColor: `color-mix(in srgb, ${accentVar} 12%, transparent)`,
              color: accentVar,
              border: `1px solid color-mix(in srgb, ${accentVar} 25%, transparent)`,
            }}
          >
            {count} {count === 1 ? 'chunk' : 'chunks'}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs font-sans-plex text-[color:var(--muted)]">
          <span>{isOpen ? 'Collapse' : 'Expand'}</span>
          {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
      </button>

      {/* Accordion Content Panel */}
      {isOpen && (
        <div
          id={`section-${id}`}
          role="region"
          aria-labelledby={`trigger-${id}`}
          className="p-4 space-y-3 border-t border-[color:var(--border-subtle)] bg-[color:var(--surface-muted)]/30 animate-fade-in"
        >
          {chunks.length === 0 ? (
            <p className="text-xs font-mono-plex text-[color:var(--muted)] text-center py-4">
              No chunks in this stage for the current query.
            </p>
          ) : (
            chunks.map((chunk, idx) => (
              <ChunkCardItem key={chunk.cache_key || idx} chunk={chunk} index={idx} accentVar={accentVar} />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function ChunkInspector({
  selectedChunks = [],
  rerankedChunks = [],
  retrievedCandidates = [],
}: ChunkInspectorProps) {
  // Expandable section states: open Selected by default, others collapsible
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    selected: true,
    reranked: false,
    retrieved: false,
  });

  const toggleSection = (key: string) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <Card className="space-y-4">
      {/* Title */}
      <div className="flex items-center justify-between pb-3 border-b border-[color:var(--border-subtle)]">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-[color:var(--primary)]" />
          <h3 className="text-sm font-brand font-semibold text-[color:var(--foreground)]">
            Context Candidate Explorer
          </h3>
        </div>
        <span className="text-xs font-mono-plex text-[color:var(--muted-foreground)]">
          3 Separate Pipeline Stages
        </span>
      </div>

      {/* 3 Separate Expandable Accordion Sections */}
      <div className="space-y-3">
        <AccordionSection
          id="selected"
          title="1. Selected Context Chunks (Phase 4 Budget Controller)"
          count={selectedChunks.length}
          icon={Sparkles}
          accentVar="var(--primary)"
          isOpen={!!openSections.selected}
          onToggle={() => toggleSection('selected')}
          chunks={selectedChunks}
        />

        <AccordionSection
          id="reranked"
          title="2. Reranked Candidates (Phase 3 Cross-Encoder)"
          count={rerankedChunks.length}
          icon={Filter}
          accentVar="var(--phase-rerank)"
          isOpen={!!openSections.reranked}
          onToggle={() => toggleSection('reranked')}
          chunks={rerankedChunks}
        />

        <AccordionSection
          id="retrieved"
          title="3. Retrieved Candidates (Phase 2 Vector Store)"
          count={retrievedCandidates.length}
          icon={Database}
          accentVar="var(--phase-retrieval)"
          isOpen={!!openSections.retrieved}
          onToggle={() => toggleSection('retrieved')}
          chunks={retrievedCandidates}
        />
      </div>
    </Card>
  );
}
