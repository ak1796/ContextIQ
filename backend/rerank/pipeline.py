from typing import Dict, Any, Optional
from backend.retrieval.retriever import retrieve_top_k
from backend.rerank.reranker import rerank, DEFAULT_RERANKER_MODEL
from backend.ingest.cache import CacheBackend


def retrieve_and_rerank(
    doc_id: str,
    question: str,
    k: int = 10,
    top_n: int = 5,
    cache: Optional[CacheBackend] = None,
    model_name: str = DEFAULT_RERANKER_MODEL,
) -> Dict[str, Any]:
    """
    Orchestrates full retrieval + reranking pipeline:
    1. Phase 2 vector search: retrieve_top_k returns top-K candidate chunks.
    2. Phase 3 cross-encoder rerank: scores candidates and returns top-N ranked chunks.
    3. Calculates total pipeline latency: total_latency_ms = retrieval_latency_ms + rerank_latency_ms.
    """
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
        model_name=model_name,
    )
    reranked_results = rerank_out.get("results", [])
    rerank_latency_ms = rerank_out.get("rerank_latency_ms", 0.0)

    total_latency_ms = round(retrieval_latency_ms + rerank_latency_ms, 2)

    return {
        "results": reranked_results,
        "retrieved_candidates": retrieved_candidates,
        "retrieval_latency_ms": retrieval_latency_ms,
        "rerank_latency_ms": rerank_latency_ms,
        "total_latency_ms": total_latency_ms,
        "doc_id": doc_id,
        "doc_version": doc_version,
    }
