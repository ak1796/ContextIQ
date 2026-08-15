"""
Guarded End-to-End Query Pipeline for CacheLingua.

Integrates input validation, context sufficiency checks, Phase 2–4 RAG steps,
sentence-level grounding validation, and output security guardrails.
"""

import time
import logging
from typing import Dict, Any, Optional

from guardrail.input_guard import validate_question
from guardrail.output_guard import validate_answer
from guardrail.grounding import check_grounding
from retrieval.retriever import retrieve_top_k
from rerank.reranker import rerank
from budget.controller import allocate_context_budget
from api.generator import generate_answer, get_groq_model
from ingest.cache import CacheBackend, get_cache

logger = logging.getLogger(__name__)

INSUFFICIENT_CONTEXT_MESSAGE = (
    "I don't have enough information in the provided documents to answer that question reliably."
)


def guarded_query_pipeline(
    doc_id: str,
    question: str,
    k: int = 10,
    top_n: int = 5,
    cache: Optional[CacheBackend] = None,
) -> Dict[str, Any]:
    """
    Executes full guarded CacheLingua query pipeline:
    Input Guard -> Phase 2 Retrieve -> Phase 3 Rerank -> Phase 4 Budget ->
    Sufficiency Check -> Groq Generation -> Output Guard & Grounding Validation.
    """
    total_start = time.perf_counter()
    if cache is None:
        cache = get_cache()

    # Step 1: Input Guardrail
    ig_start = time.perf_counter()
    input_guard = validate_question(question)
    input_guard_latency_ms = round((time.perf_counter() - ig_start) * 1000, 2)

    if not input_guard["allowed"]:
        return {
            "answer": "Your request could not be processed due to security policy.",
            "results": [],
            "selected_chunks": [],
            "retrieved_candidates": [],
            "retrieval_latency_ms": 0.0,
            "rerank_latency_ms": 0.0,
            "budget_latency_ms": 0.0,
            "generation_latency_ms": 0.0,
            "input_guard_latency_ms": input_guard_latency_ms,
            "grounding_latency_ms": 0.0,
            "output_guard_latency_ms": 0.0,
            "total_latency_ms": input_guard_latency_ms,
            "retrieved_chunks": 0,
            "reranked_chunks": 0,
            "selected_chunks_count": 0,
            "original_tokens": 0,
            "compressed_tokens": 0,
            "tokens_saved": 0,
            "compression_ratio": 1.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "context_sufficient": False,
            "answer_status": "blocked",
            "grounded": False,
            "grounding_score": 0.0,
            "unsupported_claims": [],
            "risk_level": input_guard["risk_level"],
            "reason": input_guard["reason"],
            "input_guard": input_guard,
            "output_guard": None,
            "doc_id": doc_id,
            "doc_version": 1,
            "model": get_groq_model(),
            "success": False,
            "error": input_guard["reason"],
        }

    # Step 2: Phase 2 Vector Retrieval
    ret_out = retrieve_top_k(doc_id=doc_id, question=question, k=k, cache=cache)
    retrieved_candidates = ret_out.get("results", [])
    retrieval_latency_ms = ret_out.get("retrieval_latency_ms", 0.0)
    doc_version = ret_out.get("doc_version", 1)

    # Step 3: Phase 3 Cross-Encoder Reranking
    rerank_out = rerank(
        question=question,
        chunks=retrieved_candidates,
        top_n=top_n,
    )
    reranked_results = rerank_out.get("results", [])
    rerank_latency_ms = rerank_out.get("rerank_latency_ms", 0.0)

    # Step 4: Phase 4 Budget Allocation
    budget_out = allocate_context_budget(
        question=question,
        reranked_chunks=reranked_results,
    )
    selected_chunks = budget_out.get("selected_chunks", [])
    budget_latency_ms = budget_out.get("budget_latency_ms", 0.0)

    # Step 5: Context Sufficiency Check
    context_sufficient = len(selected_chunks) > 0

    if not context_sufficient:
        total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)
        return {
            "answer": INSUFFICIENT_CONTEXT_MESSAGE,
            "results": reranked_results,
            "selected_chunks": [],
            "retrieved_candidates": retrieved_candidates,
            "retrieval_latency_ms": retrieval_latency_ms,
            "rerank_latency_ms": rerank_latency_ms,
            "budget_latency_ms": budget_latency_ms,
            "generation_latency_ms": 0.0,
            "input_guard_latency_ms": input_guard_latency_ms,
            "grounding_latency_ms": 0.0,
            "output_guard_latency_ms": 0.0,
            "total_latency_ms": total_latency_ms,
            "retrieved_chunks": len(retrieved_candidates),
            "reranked_chunks": len(reranked_results),
            "selected_chunks_count": 0,
            "context_sufficient": False,
            "answer_status": "insufficient_context",
            "grounded": True,
            "grounding_score": 1.0,
            "unsupported_claims": [],
            "risk_level": "low",
            "reason": "No relevant context chunks selected.",
            "input_guard": input_guard,
            "output_guard": None,
            "original_tokens": 0,
            "compressed_tokens": 0,
            "tokens_saved": 0,
            "compression_ratio": 1.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "model": get_groq_model(),
            "doc_id": doc_id,
            "doc_version": doc_version,
            "success": True,
            "error": None,
        }

    # Step 6: Phase 4 Groq Answer Generation
    gen_out = generate_answer(
        question=question,
        selected_chunks=selected_chunks,
    )
    generation_latency_ms = gen_out.get("generation_latency_ms", 0.0)
    raw_answer = gen_out.get("answer", "")

    # Step 7: Output Guardrail & Grounding Verification
    og_start = time.perf_counter()
    output_guard = validate_answer(
        answer=raw_answer,
        selected_chunks=selected_chunks,
        question=question,
    )
    output_guard_latency_ms = round((time.perf_counter() - og_start) * 1000, 2)

    final_answer = raw_answer
    grounded = output_guard["grounded"]
    grounding_score = output_guard["grounding_score"]

    if not output_guard["allowed"]:
        if "secret leakage" in (output_guard.get("reason") or "").lower():
            final_answer = "Response blocked due to security policy."
            answer_status = "blocked"
        else:
            final_answer = INSUFFICIENT_CONTEXT_MESSAGE
            answer_status = "insufficient_context"
    else:
        if grounded is True:
            answer_status = "grounded"
        elif grounded == "partial":
            answer_status = "partially_grounded"
        else:
            answer_status = "unsupported"

    total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)

    # Get grounding detail
    grounding_detail = check_grounding(answer=raw_answer, selected_chunks=selected_chunks)
    unsupported_claims = grounding_detail.get("unsupported_claims", [])

    return {
        "answer": final_answer,
        "results": reranked_results,
        "selected_chunks": selected_chunks,
        "retrieved_candidates": retrieved_candidates,

        # Latency breakdown (ms)
        "input_guard_latency_ms": input_guard_latency_ms,
        "retrieval_latency_ms": retrieval_latency_ms,
        "rerank_latency_ms": rerank_latency_ms,
        "budget_latency_ms": budget_latency_ms,
        "generation_latency_ms": generation_latency_ms,
        "output_guard_latency_ms": output_guard_latency_ms,
        "total_latency_ms": total_latency_ms,

        # Chunk counts
        "retrieved_chunks": len(retrieved_candidates),
        "reranked_chunks": len(reranked_results),
        "selected_chunks_count": len(selected_chunks),

        # Guardrail & Grounding Status
        "context_sufficient": context_sufficient,
        "answer_status": answer_status,
        "grounded": grounded,
        "grounding_score": grounding_score,
        "unsupported_claims": unsupported_claims,
        "risk_level": output_guard["risk_level"],
        "reason": output_guard.get("reason"),
        "input_guard": input_guard,
        "output_guard": output_guard,

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
        "error": gen_out.get("error"),
    }
