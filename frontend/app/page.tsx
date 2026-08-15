'use client';

import React, { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { MetricCard } from '@/components/metrics/MetricCard';
import { LatencyBar } from '@/components/metrics/LatencyBar';
import { ContextEfficiencyCard } from '@/components/metrics/ContextEfficiencyCard';
import { GroundingCard } from '@/components/guardrails/GroundingCard';
import { DocumentInfoCard } from '@/components/documents/DocumentInfoCard';
import { DocumentManagerView } from '@/components/documents/DocumentManagerView';
import { QueryInput } from '@/components/chat/QueryInput';
import { ResponseView } from '@/components/chat/ResponseView';
import { ChunkInspector } from '@/components/context/ChunkInspector';
import { queryPipeline, getApiBaseUrl } from '@/lib/api';
import { QueryResponse } from '@/lib/types';
import { formatMs, formatPercentage } from '@/lib/utils';
import { Clock, Zap, ShieldCheck, Database, AlertCircle, Sparkles } from 'lucide-react';

export default function Dashboard() {
  const [activeTab, setActiveTab]         = useState('query');
  const [selectedDocId, setSelectedDocId] = useState('doc1.txt');
  const [isLoading, setIsLoading]         = useState(false);
  const [error, setError]                 = useState<string | null>(null);
  const [queryResult, setQueryResult]     = useState<QueryResponse | null>(null);

  const apiBaseUrl = getApiBaseUrl();

  const handleQuerySubmit = async (payload: {
    doc_id: string;
    question: string;
    k: number;
    top_n: number;
  }) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await queryPipeline(payload);
      setQueryResult(data);
      if (data.doc_id) {
        setSelectedDocId(data.doc_id);
      }
    } catch (err: unknown) {
      console.error('Pipeline execution error:', err);
      setError(err instanceof Error ? err.message : 'Failed to execute query pipeline.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSecurityTestSelect = (testQuery: string) => {
    setActiveTab('query');
    handleQuerySubmit({
      doc_id: selectedDocId,
      question: testQuery,
      k: 4,
      top_n: 2,
    });
  };

  const handleSelectDocumentForQuery = (docId: string) => {
    setSelectedDocId(docId);
    setActiveTab('query');
  };

  return (
    <div className="flex flex-1" style={{ minHeight: 'calc(100vh - 57px)' }}>
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedDocId={selectedDocId}
        onSelectDocId={setSelectedDocId}
      />

      {/* Main Workspace Area */}
      <main className="flex-1 p-4 md:p-6 space-y-6 overflow-y-auto max-w-7xl mx-auto w-full">

        {/* ── Metric Cards Header Bar ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Latency"
            value={formatMs(queryResult?.total_latency_ms ?? 0)}
            subtitle="Pipeline roundtrip time"
            icon={Clock}
            iconColor="var(--phase-retrieval)"
            trend={queryResult ? `${queryResult.generation_latency_ms.toFixed(0)} ms LLM` : 'Ready'}
            trendType="neutral"
          />

          <MetricCard
            title="Token Reduction"
            value={queryResult ? `${queryResult.tokens_saved} saved` : '—'}
            subtitle={queryResult
              ? `${queryResult.compressed_tokens} / ${queryResult.original_tokens} tokens`
              : 'LLMLingua-2 compressed'}
            icon={Zap}
            iconColor="var(--phase-budget)"
            trend={queryResult ? `${((1 - queryResult.compression_ratio) * 100).toFixed(1)}% saved` : '0%'}
            trendType="positive"
          />

          <MetricCard
            title="Grounding Score"
            value={queryResult ? formatPercentage(queryResult.grounding_score) : '—'}
            subtitle={queryResult ? `Status: ${queryResult.answer_status}` : 'Sentence-level check'}
            icon={ShieldCheck}
            iconColor="var(--success)"
            trend={queryResult ? `Risk: ${queryResult.risk_level.toUpperCase()}` : 'LOW RISK'}
            trendType={queryResult?.risk_level === 'high' ? 'negative' : 'positive'}
          />

          <MetricCard
            title="Chunks Selected"
            value={queryResult ? `${queryResult.selected_chunks_count} / ${queryResult.retrieved_chunks}` : '—'}
            subtitle={queryResult
              ? `Reranked: ${queryResult.reranked_chunks}`
              : 'Budget controller limit'}
            icon={Database}
            iconColor="var(--phase-rerank)"
            trend={queryResult ? `${queryResult.doc_id} v${queryResult.doc_version}` : selectedDocId}
            trendType="neutral"
          />
        </div>

        {/* ── Tab 1: Query Bench View ── */}
        {activeTab === 'query' && (
          <div className="space-y-6">
            {/* Input Query Bar */}
            <QueryInput
              onSubmit={handleQuerySubmit}
              isLoading={isLoading}
              selectedDocId={selectedDocId}
              onDocIdChange={setSelectedDocId}
            />

            {/* Error Banner */}
            {error && (
              <div
                role="alert"
                className="p-4 rounded-xl flex items-center gap-3 text-xs font-sans-plex animate-fade-in"
                style={{
                  backgroundColor: `color-mix(in srgb, var(--danger) 8%, transparent)`,
                  border: `1px solid color-mix(in srgb, var(--danger) 25%, transparent)`,
                  color: 'var(--danger)',
                }}
              >
                <AlertCircle className="h-5 w-5 shrink-0" />
                <div>
                  <span className="font-semibold block">Execution Failed:</span>
                  <span>{error}</span>
                  <span
                    className="block mt-1 text-[11px] font-mono-plex"
                    style={{ color: 'var(--muted)' }}
                  >
                    Ensure FastAPI backend is reachable at {apiBaseUrl}
                  </span>
                </div>
              </div>
            )}

            {/* Empty State when no query has been submitted yet */}
            {!queryResult && !isLoading && !error && (
              <div
                className="p-8 rounded-xl text-center space-y-3"
                style={{
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div
                  className="h-10 w-10 mx-auto rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: 'var(--surface-elevated)' }}
                >
                  <Sparkles className="h-5 w-5 text-[color:var(--primary)]" />
                </div>
                <div>
                  <h3 className="text-sm font-brand font-semibold text-[color:var(--foreground)]">
                    Query Bench Ready
                  </h3>
                  <p className="text-xs font-sans-plex text-[color:var(--muted)] mt-1 max-w-md mx-auto">
                    Select a target document or enter a question above to execute the guarded CacheLingua pipeline (Retrieval → Reranking → Context Budget → Groq Generation → Guardrails).
                  </p>
                </div>
              </div>
            )}

            {/* Active Query Results & Observability Dashboard */}
            {queryResult && (
              <div className="space-y-6 animate-fade-in">

                {/* Primary Response & Latency Column */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ResponseView data={queryResult} />
                  <LatencyBar
                    inputGuardMs={queryResult.input_guard_latency_ms}
                    retrievalMs={queryResult.retrieval_latency_ms}
                    rerankMs={queryResult.rerank_latency_ms}
                    budgetMs={queryResult.budget_latency_ms}
                    generationMs={queryResult.generation_latency_ms}
                    outputGuardMs={queryResult.output_guard_latency_ms}
                    totalMs={queryResult.total_latency_ms}
                  />
                </div>

                {/* Grounding & Security Card */}
                <GroundingCard
                  grounding_score={queryResult.grounding_score}
                  grounded={queryResult.grounded}
                  unsupported_claims={queryResult.unsupported_claims}
                  answer_status={queryResult.answer_status}
                  risk_level={queryResult.risk_level}
                />

                {/* Context & Token Efficiency Metrics Card */}
                <ContextEfficiencyCard
                  originalTokens={queryResult.original_tokens}
                  compressedTokens={queryResult.compressed_tokens}
                  tokensSaved={queryResult.tokens_saved}
                  compressionRatio={queryResult.compression_ratio}
                  retrievedChunks={queryResult.retrieved_chunks}
                  rerankedChunks={queryResult.reranked_chunks}
                  selectedChunks={queryResult.selected_chunks_count}
                />

                {/* Target Document & System Info Card */}
                <DocumentInfoCard
                  docId={queryResult.doc_id}
                  docVersion={queryResult.doc_version}
                  model={queryResult.model}
                />

                {/* 3 Separate Expandable Candidate Accordion Sections */}
                <ChunkInspector
                  selectedChunks={queryResult.selected_chunks}
                  rerankedChunks={queryResult.results}
                  retrievedCandidates={queryResult.retrieved_candidates}
                />
              </div>
            )}
          </div>
        )}

        {/* ── Tab 2: Document Ingest & Management ── */}
        {activeTab === 'documents' && (
          <DocumentManagerView onSelectDocumentForQuery={handleSelectDocumentForQuery} />
        )}

        {/* ── Tab 3: Token Analytics ── */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <ContextEfficiencyCard
              originalTokens={queryResult?.original_tokens ?? 0}
              compressedTokens={queryResult?.compressed_tokens ?? 0}
              tokensSaved={queryResult?.tokens_saved ?? 0}
              compressionRatio={queryResult?.compression_ratio ?? 1.0}
              retrievedChunks={queryResult?.retrieved_chunks ?? 0}
              rerankedChunks={queryResult?.reranked_chunks ?? 0}
              selectedChunks={queryResult?.selected_chunks_count ?? 0}
            />
          </div>
        )}

        {/* ── Tab 4: Guardrail Audit ── */}
        {activeTab === 'guardrails' && (
          <div className="space-y-6">
            <GroundingCard
              grounding_score={queryResult?.grounding_score ?? 0}
              grounded={queryResult?.grounded ?? true}
              unsupported_claims={queryResult?.unsupported_claims ?? []}
              answer_status={queryResult?.answer_status ?? 'grounded'}
              risk_level={queryResult?.risk_level ?? 'low'}
              onSelectTestQuery={handleSecurityTestSelect}
            />
          </div>
        )}

        {/* ── Tab 5: Vector Store & Document Metadata ── */}
        {activeTab === 'vectorstore' && (
          <div className="space-y-6">
            <DocumentInfoCard
              docId={queryResult?.doc_id ?? selectedDocId}
              docVersion={queryResult?.doc_version ?? 1}
              model={queryResult?.model ?? 'llama-3.3-70b-versatile'}
            />
          </div>
        )}
      </main>
    </div>
  );
}
