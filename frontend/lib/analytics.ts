/**
 * Phase 8 — Observability API helpers.
 * Fetches system health, analytics summary, and recent query records
 * from the FastAPI backend.
 */

import { getApiBaseUrl } from '@/lib/api';

export interface SystemHealth {
  status: 'healthy' | 'degraded';
  backend: boolean;
  redis: 'connected' | 'unavailable';
  vector_store: 'healthy' | 'unavailable';
  llm: 'available' | 'unconfigured';
  documents: number;
  timestamp: string;
}

export interface AnalyticsSummary {
  total_queries: number;
  successful_queries: number;
  blocked_queries: number;
  insufficient_context_queries: number;
  average_latency_ms: number;
  average_retrieval_latency_ms: number;
  average_rerank_latency_ms: number;
  average_generation_latency_ms: number;
  average_grounding_score: number;
  grounded_response_pct: number;
  average_compression_ratio: number;
  total_tokens_saved: number;
  average_retrieved_chunks: number;
  average_selected_chunks: number;
}

export interface RecentQueryRecord {
  timestamp: string;
  doc_id: string;
  answer_status: string;
  success: number;
  grounding_score: number;
  total_latency_ms: number;
  tokens_saved: number;
  retrieved_chunks: number;
  selected_chunks_count: number;
  compression_ratio: number;
  input_guard_status: string;
  output_guard_status: string;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/system/health`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/analytics/summary`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Analytics summary failed: ${res.status}`);
  return res.json();
}

export async function fetchRecentQueries(limit = 50): Promise<RecentQueryRecord[]> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/analytics/recent?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Recent queries failed: ${res.status}`);
  const data = await res.json();
  return data.queries ?? [];
}
