export interface Chunk {
  chunk_index: number;
  original_text: string;
  compressed_text: string;
  cache_key: string;
  doc_id?: string;
  doc_version?: number;
  similarity_score?: number;
  relevance_score?: number;
  token_count_before?: number;
  token_count_after?: number;
}

export interface GuardResult {
  allowed: boolean;
  reason: string | null;
  risk_level: 'low' | 'medium' | 'high';
}

export interface OutputGuardResult {
  allowed: boolean;
  grounded: boolean | 'partial';
  grounding_score: number;
  risk_level: 'low' | 'medium' | 'high';
  reason: string | null;
}

export interface QueryResponse {
  answer: string;
  results: Chunk[];
  selected_chunks: Chunk[];
  retrieved_candidates: Chunk[];
  
  // Latency breakdown (ms)
  input_guard_latency_ms: number;
  retrieval_latency_ms: number;
  rerank_latency_ms: number;
  budget_latency_ms: number;
  generation_latency_ms: number;
  output_guard_latency_ms: number;
  total_latency_ms: number;
  
  // Chunk counts
  retrieved_chunks: number;
  reranked_chunks: number;
  selected_chunks_count: number;
  
  // Guardrail & Grounding Status
  context_sufficient: boolean;
  answer_status: 'grounded' | 'partially_grounded' | 'insufficient_context' | 'blocked' | 'unsupported';
  grounded: boolean | 'partial';
  grounding_score: number;
  unsupported_claims: string[];
  risk_level: 'low' | 'medium' | 'high';
  reason: string | null;
  input_guard?: GuardResult | null;
  output_guard?: OutputGuardResult | null;
  
  // Compression & Token Metrics
  original_tokens: number;
  compressed_tokens: number;
  tokens_saved: number;
  compression_ratio: number;
  
  // Groq Usage Metrics
  prompt_tokens: number;
  completion_tokens: number;
  
  // Metadata
  model: string;
  doc_id: string;
  doc_version: number;
  success: boolean;
  error: string | null;
}

export interface QueryPayload {
  doc_id: string;
  question: string;
  k?: number;
  top_n?: number;
}

export interface HealthResponse {
  status: string;
}

export interface DocumentMetadata {
  doc_id: string;
  doc_version: number;
  filename: string;
  size: number;
  status: 'indexed' | 'processing' | 'failed' | 'deleted';
  chunk_count: number;
  created_at: string;
  updated_at?: string | null;
}

export interface DocumentUploadResponse {
  success: boolean;
  message: string;
  document?: DocumentMetadata | null;
  ingestion_summary?: {
    doc_id: string;
    doc_version: number;
    total_chunks: number;
    evicted_count?: number;
  } | null;
}

export interface DocumentListResponse {
  documents: DocumentMetadata[];
}
