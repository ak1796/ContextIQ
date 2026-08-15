"""
Full End-to-End Query Pipeline for CacheLingua.

Orchestrates all 4 phases:
1. Document retrieval via ChromaDB vector index (Phase 2).
2. Cross-Encoder candidate reranking (Phase 3).
3. Calibrated context token budget allocation (Phase 4).
4. Grounded Groq LLM answer generation (Phase 4).

Exposes full observability metrics including latencies, chunk counts, token savings, and compression ratios.
"""

import time
import logging
from typing import Dict, Any, Optional

from retrieval.retriever import retrieve_top_k
from rerank.reranker import rerank
from budget.controller import allocate_context_budget
from api.generator import generate_answer, get_groq_model
from ingest.cache import CacheBackend, get_cache

logger = logging.getLogger(__name__)


def query_pipeline(
    doc_id: str,
    question: str,
    k: int = 10,
    top_n: int = 5,
    cache: Optional[CacheBackend] = None,
) -> Dict[str, Any]:
    """
    Executes complete end-to-end CacheLingua RAG pipeline:
    retrieve -> rerank -> budget -> generate.
    """
    if cache is None:
        cache = get_cache()

    # Step 1: Phase 2 Vector Retrieval
    ret_out = retrieve_top_k(doc_id=doc_id, question=question, k=k, cache=cache)
    retrieved_candidates = ret_out.get("results", [])
    retrieval_latency_ms = ret_out.get("retrieval_latency_ms", 0.0)
    doc_version = ret_out.get("doc_version", 1)

    # Step 2: Phase 3 Cross-Encoder Reranking
    rerank_out = rerank(
        question=question,
        chunks=retrieved_candidates,
        top_n=top_n,
    )
    reranked_results = rerank_out.get("results", [])
    rerank_latency_ms = rerank_out.get("rerank_latency_ms", 0.0)

    # Step 3: Phase 4 Budget Allocation
    budget_out = allocate_context_budget(
        question=question,
        reranked_chunks=reranked_results,
    )
    selected_chunks = budget_out.get("selected_chunks", [])
    budget_latency_ms = budget_out.get("budget_latency_ms", 0.0)

    # Step 4: Phase 4 Groq Answer Generation
    gen_out = generate_answer(
        question=question,
        selected_chunks=selected_chunks,
    )
    generation_latency_ms = gen_out.get("generation_latency_ms", 0.0)

    # Calculate total latency
    total_latency_ms = round(
        retrieval_latency_ms + rerank_latency_ms + budget_latency_ms + generation_latency_ms,
        2,
    )

    return {
        "answer": gen_out.get("answer", ""),
        "results": reranked_results,
        "selected_chunks": selected_chunks,
        "retrieved_candidates": retrieved_candidates,

        # Latencies (ms)
        "retrieval_latency_ms": retrieval_latency_ms,
        "rerank_latency_ms": rerank_latency_ms,
        "budget_latency_ms": budget_latency_ms,
        "generation_latency_ms": generation_latency_ms,
        "total_latency_ms": total_latency_ms,

        # Counts
        "retrieved_chunks": len(retrieved_candidates),
        "reranked_chunks": len(reranked_results),
        "selected_chunks_count": len(selected_chunks),

        # Compression & Token Metrics
        "original_tokens": budget_out.get("original_tokens", 0),
        "compressed_tokens": budget_out.get("compressed_tokens", 0),
        "tokens_saved": budget_out.get("tokens_saved", 0),
        "compression_ratio": budget_out.get("compression_ratio", 1.0),

        # Groq Usage Metrics
        "prompt_tokens": gen_out.get("prompt_tokens", 0),
        "completion_tokens": gen_out.get("completion_tokens", 0),

        # Model & Metadata
        "model": gen_out.get("model", get_groq_model()),
        "doc_id": doc_id,
        "doc_version": doc_version,
        "success": gen_out.get("success", True),
        "error": gen_out.get("error", None),
    }
