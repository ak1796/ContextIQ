"""
Guarded End-to-End Query Pipeline for CacheLingua.

Integrates input validation, context sufficiency checks, Phase 2–4 RAG steps,
sentence-level grounding validation, and output security guardrails.
"""

import time
import logging
from typing import Dict, Any, Optional

from backend.guardrail.input_guard import validate_question
from backend.guardrail.output_guard import validate_answer
from backend.guardrail.grounding import check_grounding
from backend.retrieval.retriever import retrieve_top_k
from backend.rerank.reranker import rerank
from backend.budget.controller import allocate_context_budget
from backend.api.generator import generate_answer, get_groq_model
from backend.ingest.cache import CacheBackend, get_cache
from backend.budget.controller import DEFAULT_MAX_OUTPUT_TOKENS
from backend.retrieval.hybrid import get_tabular_dataframe, is_structured_lookup, filter_tabular_dataframe

logger = logging.getLogger(__name__)
import os

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
    Input Guard -> Hybrid Routing -> Phase 2 Retrieve -> Phase 3 Rerank -> Phase 4 Budget ->
    Sufficiency Check -> Groq Generation -> Output Guard & Grounding Validation.
    """
    total_start = time.perf_counter()
    if cache is None:
        cache = get_cache()

    # Step 1: Input Guardrail
    ig_start = time.perf_counter()
    input_guard = validate_question(question)
    input_guard_latency_ms = round((time.perf_counter() - ig_start) * 1000, 2)
    print(f"[INPUT_GUARD] allowed={input_guard['allowed']}, risk_level={input_guard.get('risk_level')}, reason={input_guard.get('reason')}")

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

    # Hybrid Routing Check for Structured CSV Lookup
    df_tabular = get_tabular_dataframe(doc_id)
    structured_match = None
    if df_tabular is not None and not df_tabular.empty:
        structured_match = is_structured_lookup(question, df_columns=list(df_tabular.columns))

    if structured_match is not None and df_tabular is not None:
        print("[ROUTING] structured_lookup")
        col_name = structured_match["column"]
        val_num = structured_match["value"]
        matched_df = filter_tabular_dataframe(df_tabular, col_name, val_num, structured_match.get("operator", "=="))

        if matched_df.empty:
            # Requirement 4: Value not present in CSV, skip LLM call entirely
            total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)
            val_str = int(val_num) if isinstance(val_num, float) and val_num.is_integer() else val_num
            no_rec_msg = f"No record found with {col_name} = {val_str} in the dataset"
            return {
                "answer": no_rec_msg,
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
                "total_latency_ms": total_latency_ms,
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
                "answer_status": "no_record_found",
                "grounded": True,
                "grounding_score": 1.0,
                "unsupported_claims": [],
                "risk_level": "low",
                "reason": no_rec_msg,
                "input_guard": input_guard,
                "output_guard": None,
                "doc_id": doc_id,
                "doc_version": 1,
                "routing": "structured_lookup",
                "model": get_groq_model(),
                "success": True,
                "error": None,
            }

        # Build context directly from exact matching rows
        selected_chunks = []
        doc_label = doc_id.split('.')[0].split('/')[-1].split('\\')[-1] if doc_id else ""
        doc_prefix = f"Entity: {doc_label} | " if doc_label else ""
        import pandas as pd
        for idx, (_, row) in enumerate(matched_df.iterrows(), start=1):
            pairs = [f"{c}: {v}" for c, v in row.items() if pd.notna(v)]
            row_str = f"{doc_prefix}Record {idx}: " + ", ".join(pairs)
            selected_chunks.append({
                "chunk_index": idx - 1,
                "original_text": row_str,
                "compressed_text": row_str,
                "score": 1.0,
                "doc_id": doc_id,
            })

        retrieved_candidates = selected_chunks
        reranked_results = selected_chunks
        retrieval_latency_ms = 0.0
        rerank_latency_ms = 0.0
        budget_latency_ms = 0.0
        doc_version = 1
        budget_out = {
            "original_tokens": sum(len(c["original_text"].split()) for c in selected_chunks),
            "compressed_tokens": sum(len(c["compressed_text"].split()) for c in selected_chunks),
            "tokens_saved": 0,
            "compression_ratio": 1.0,
        }
    else:
        print("[ROUTING] semantic_pipeline")
        # Step 2: Phase 2 Vector Retrieval
        try:
            ret_out = retrieve_top_k(doc_id=doc_id, question=question, k=k, cache=cache)
            retrieved_candidates = ret_out.get("results", [])
            retrieval_latency_ms = ret_out.get("retrieval_latency_ms", 0.0)
            doc_version = ret_out.get("doc_version", 1)
            print(f"[RETRIEVAL] retrieved {len(retrieved_candidates)} candidates in {retrieval_latency_ms}ms")
        except Exception as e:
            print(f"[RETRIEVAL ERROR] {e}")
            raise

        # Step 3: Phase 3 Cross-Encoder Reranking
        try:
            rerank_out = rerank(
                question=question,
                chunks=retrieved_candidates,
                top_n=top_n,
            )
            reranked_results = rerank_out.get("results", [])
            rerank_latency_ms = rerank_out.get("rerank_latency_ms", 0.0)
            print(f"[RERANK] reranked to {len(reranked_results)} results in {rerank_latency_ms}ms")
        except Exception as e:
            print(f"[RERANK ERROR] {e}")
            raise

        # Step 4: Phase 4 Budget Allocation
        try:
            budget_out = allocate_context_budget(
                question=question,
                reranked_chunks=reranked_results,
            )
            selected_chunks = budget_out.get("selected_chunks", [])
            budget_latency_ms = budget_out.get("budget_latency_ms", 0.0)
            print(f"[BUDGET] selected {len(selected_chunks)} chunks in {budget_latency_ms}ms")
        except Exception as e:
            print(f"[BUDGET ERROR] {e}")
            raise

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
    try:
        # Debug: token counts and context details
        import tiktoken, json
        enc = tiktoken.get_encoding("gpt2")
        context_text = " ".join([c.get("compressed_text") or c.get("original_text") or "" for c in selected_chunks])
        char_len = len(context_text)
        token_len = len(enc.encode(context_text))
        print(f"[CONTEXT] char_len={char_len}, token_len={token_len}, max_context={os.getenv('MAX_CONTEXT_TOKENS', '4000')}")
        print(f"[CONTEXT] first 300 chars: {context_text[:300]}")
        max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS))
        temperature = 0.1  # currently hardcoded
        print(f"[GROQ REQUEST] max_tokens={max_tokens}, temperature={temperature}")
        # Generate answer
        gen_out = generate_answer(
            question=question,
            selected_chunks=selected_chunks,
        )
        generation_latency_ms = gen_out.get("generation_latency_ms", 0.0)
        raw_answer = gen_out.get("answer", "")
        # Print raw response details
        if "error" in gen_out and gen_out["error"]:
            print(f"[GROQ RESPONSE ERROR] {gen_out['error']}")
        else:
            print(f"[GROQ RESPONSE] model={gen_out.get('model')}, prompt_tokens={gen_out.get('prompt_tokens')}, completion_tokens={gen_out.get('completion_tokens')}" )
        if not raw_answer:
            print("[GROQ RESPONSE] Empty answer received")
    except Exception as e:
        print(f"[GENERATION ERROR] {e}")
        raise

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
    print(f"[GROUNDING] score={grounding_detail.get('grounding_score')}, partial_inflate={grounding_detail.get('partial_inflate')}")

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
