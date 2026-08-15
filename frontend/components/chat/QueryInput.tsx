'use client';

import React, { useState } from 'react';
import { Send, FileText, Sliders, Sparkles, Loader2, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';

interface QueryInputProps {
  onSubmit: (payload: { doc_id: string; question: string; k: number; top_n: number }) => void;
  isLoading: boolean;
  selectedDocId?: string;
  onDocIdChange?: (docId: string) => void;
}

const MAX_QUESTION_LENGTH = 1000;

const SAMPLE_QUERIES = [
  'How are cache keys generated for stored document chunks?',
  'What methods improve retrieval efficiency in modern RAG systems?',
  'How does prompt compression reduce LLM inference latency?',
];

export function QueryInput({ onSubmit, isLoading, selectedDocId = 'doc1.txt', onDocIdChange }: QueryInputProps) {
  const [internalDocId, setInternalDocId] = useState<string | null>(null);
  const docId = internalDocId ?? selectedDocId;

  const [question, setQuestion]   = useState('');
  const [k, setK]                 = useState(4);
  const [topN, setTopN]           = useState(2);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [inputError, setInputError]     = useState<string | null>(null);

  const handleDocChange = (newDoc: string) => {
    setInternalDocId(newDoc);
    if (onDocIdChange) {
      onDocIdChange(newDoc);
    }
  };

  const handleQuestionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    if (val.length > MAX_QUESTION_LENGTH) {
      setInputError(`Question length exceeds maximum limit of ${MAX_QUESTION_LENGTH} characters.`);
    } else {
      setInputError(null);
    }
    setQuestion(val);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setInputError('Please enter a question before submitting.');
      return;
    }
    if (trimmed.length > MAX_QUESTION_LENGTH) {
      setInputError(`Question length exceeds limit of ${MAX_QUESTION_LENGTH} characters.`);
      return;
    }
    if (!docId.trim()) {
      setInputError('Document ID cannot be empty.');
      return;
    }
    if (isLoading) return;

    setInputError(null);
    onSubmit({ doc_id: docId.trim(), question: trimmed, k, top_n: topN });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit(e);
    }
  };

  const isOverLength = question.length > MAX_QUESTION_LENGTH;
  const isSubmitDisabled = !question.trim() || isLoading || isOverLength || !docId.trim();

  return (
    <Card glow>
      <form onSubmit={handleSubmit} className="space-y-4">

        {/* Target Document & Advanced Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <FileText className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--primary)' }} />
            <label
              htmlFor="doc-id-input"
              className="text-xs font-sans-plex"
              style={{ color: 'var(--muted)' }}
            >
              Document Target:
            </label>
            <input
              id="doc-id-input"
              type="text"
              value={docId}
              disabled={isLoading}
              onChange={(e) => handleDocChange(e.target.value)}
              placeholder="e.g. doc1.txt"
              className="px-2.5 py-1 text-xs font-mono-plex rounded-md border outline-none transition-all disabled:opacity-50 w-32"
              style={{
                backgroundColor: 'var(--surface-muted)',
                borderColor: 'var(--border)',
                color: 'var(--foreground)',
              }}
            />
          </div>

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-sans-plex rounded-md transition-colors"
            style={{
              backgroundColor: 'var(--surface-muted)',
              border: '1px solid var(--border)',
              color: 'var(--muted)',
            }}
          >
            <Sliders className="h-3.5 w-3.5" style={{ color: 'var(--primary)' }} />
            Parameters (k={k}, top_n={topN})
          </button>
        </div>

        {/* Advanced Sliders */}
        {showAdvanced && (
          <div
            className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-3 rounded-lg text-xs font-mono-plex"
            style={{
              backgroundColor: 'var(--surface-muted)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div>
              <div className="flex justify-between mb-1.5" style={{ color: 'var(--muted)' }}>
                <span>Top-K retrieved (k):</span>
                <span style={{ color: 'var(--primary)', fontWeight: 600 }}>{k}</span>
              </div>
              <input
                type="range" min="1" max="20" value={k}
                disabled={isLoading}
                onChange={(e) => setK(Number(e.target.value))}
                className="w-full"
                style={{ accentColor: 'var(--primary)' }}
              />
            </div>
            <div>
              <div className="flex justify-between mb-1.5" style={{ color: 'var(--muted)' }}>
                <span>Top-N reranked (top_n):</span>
                <span style={{ color: 'var(--phase-rerank)', fontWeight: 600 }}>{topN}</span>
              </div>
              <input
                type="range" min="1" max="10" value={topN}
                disabled={isLoading}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="w-full"
                style={{ accentColor: 'var(--phase-rerank)' }}
              />
            </div>
          </div>
        )}

        {/* Textarea */}
        <div className="relative">
          <textarea
            value={question}
            disabled={isLoading}
            onChange={handleQuestionChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about the document context… (Ctrl+Enter to submit)"
            rows={3}
            className="w-full px-3.5 py-3 text-sm font-sans-plex rounded-xl resize-none outline-none transition-all disabled:opacity-60"
            style={{
              backgroundColor: 'var(--surface-muted)',
              border: isOverLength ? '1px solid var(--danger)' : '1px solid var(--border)',
              color: 'var(--foreground)',
            }}
            onFocus={(e) => {
              if (!isOverLength) e.currentTarget.style.borderColor = 'var(--primary)';
            }}
            onBlur={(e) => {
              if (!isOverLength) e.currentTarget.style.borderColor = 'var(--border)';
            }}
          />

          {/* Character count & Submit button */}
          <div className="flex items-center justify-between mt-2">
            <span
              className="text-[11px] font-mono-plex"
              style={{
                color: isOverLength ? 'var(--danger)' : 'var(--muted-foreground)',
              }}
            >
              {question.length} / {MAX_QUESTION_LENGTH} chars
            </span>

            <button
              type="submit"
              disabled={isSubmitDisabled}
              className="flex items-center gap-2 px-4 py-2 text-xs font-sans-plex font-semibold rounded-lg transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--primary)',
                color: 'var(--primary-foreground)',
              }}
            >
              {isLoading ? (
                <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Processing Query…</>
              ) : (
                <><Send className="h-3.5 w-3.5" /> Ask Question</>
              )}
            </button>
          </div>
        </div>

        {/* Validation Error Banner */}
        {inputError && (
          <div
            className="p-2.5 rounded-lg flex items-center gap-2 text-xs font-sans-plex"
            style={{
              backgroundColor: `color-mix(in srgb, var(--danger) 10%, transparent)`,
              border: `1px solid color-mix(in srgb, var(--danger) 25%, transparent)`,
              color: 'var(--danger)',
            }}
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{inputError}</span>
          </div>
        )}
      </form>

      {/* Sample queries */}
      <div className="mt-4 pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
        <span
          className="text-[10px] font-mono-plex uppercase tracking-widest block mb-2"
          style={{ color: 'var(--muted-foreground)' }}
        >
          Sample Queries:
        </span>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_QUERIES.map((q, idx) => (
            <button
              key={idx}
              type="button"
              disabled={isLoading}
              onClick={() => {
                setQuestion(q);
                setInputError(null);
              }}
              className="text-xs px-2.5 py-1 rounded-md border font-sans-plex flex items-center gap-1.5 transition-all text-left disabled:opacity-50"
              style={{
                backgroundColor: 'var(--surface-muted)',
                color: 'var(--muted)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              <Sparkles className="h-3 w-3 shrink-0" style={{ color: 'var(--primary)' }} />
              <span className="truncate max-w-[260px]">{q}</span>
            </button>
          ))}
        </div>
      </div>
    </Card>
  );
}
