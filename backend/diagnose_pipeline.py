"""
Diagnostic & Tracing Tool for ContextIQ RAG Pipeline (Phase 7.2).
Traces every pipeline stage for a target question and document to identify exact failure points.
"""

import json
import logging
from typing import Dict, Any

from backend.guardrail.input_guard import validate_question
from backend.retrieval.retriever import retrieve_top_k
from backend.rerank.reranker import rerank
from backend.budget.controller import allocate_context_budget
from backend.api.generator import generate_answer, get_groq_model
from backend.guardrail.grounding import check_grounding
from backend.guardrail.output_guard import validate_answer
from backend.ingest.cache import get_cache

logger = logging.getLogger(__name__)


def trace_pipeline(doc_id: str, question: str, k: int = 10, top_n: int = 5) -> Dict[str, Any]:
    cache = get_cache()

    print("=" * 80)
    print(f"       CONTEXTIQ PIPELINE DIAGNOSTIC TRACE")
    print("=" * 80)
    print(f"QUESTION: {question}")
    print(f"TARGET DOC_ID: {doc_id}")

    # Step 1: Input Guard
    ig = validate_question(question)
    print(f"\n--- STAGE 1: INPUT GUARD ---")
    print(f"Allowed: {ig['allowed']} | Risk Level: {ig['risk_level']} | Reason: {ig['reason']}")
    if not ig['allowed']:
        print("Pipeline stopped at Stage 1 (Input Guard).")
        return {"stopped_at": "input_guard"}

    # Step 2: Vector Retrieval
    ret_out = retrieve_top_k(doc_id=doc_id, question=question, k=k, cache=cache)
    retrieved_candidates = ret_out.get("results", [])
    doc_version = ret_out.get("doc_version", 1)

    print(f"\n--- STAGE 2: RETRIEVAL (Doc Version: {doc_version}) ---")
    print(f"Retrieved Chunks Count: {len(retrieved_candidates)}")
    for i, c in enumerate(retrieved_candidates):
        sim = c.get("similarity_score", 0.0)
        txt = (c.get("compressed_text") or c.get("original_text") or "")[:100]
        print(f"  [{i}] Chunk Index: {c.get('chunk_index')} | Sim Score: {sim:.4f} | Preview: {txt}...")

    # Step 3: CrossEncoder Reranking
    rerank_out = rerank(question=question, chunks=retrieved_candidates, top_n=top_n)
    reranked_results = rerank_out.get("results", [])

    print(f"\n--- STAGE 3: RERANKING ---")
    print(f"Reranked Chunks Count: {len(reranked_results)}")
    for i, c in enumerate(reranked_results):
        rel = c.get("relevance_score", 0.0)
        txt = (c.get("compressed_text") or c.get("original_text") or "")[:100]
        print(f"  [{i}] Chunk Index: {c.get('chunk_index')} | Rel Score: {rel:.4f} | Preview: {txt}...")

    # Step 4: Context Budget Allocation
    budget_out = allocate_context_budget(question=question, reranked_chunks=reranked_results)
    selected_chunks = budget_out.get("selected_chunks", [])

    print(f"\n--- STAGE 4: BUDGET ALLOCATION ---")
    print(f"Selected Chunks Count: {len(selected_chunks)} / {len(reranked_results)}")
    for i, c in enumerate(selected_chunks):
        txt = (c.get("compressed_text") or c.get("original_text") or "")[:100]
        print(f"  [{i}] Chunk Index: {c.get('chunk_index')} | Preview: {txt}...")

    # Step 5: Final Context Supplied to Groq LLM
    context_blocks = []
    for idx, chunk in enumerate(selected_chunks, 1):
        t = chunk.get("compressed_text") or chunk.get("original_text") or ""
        context_blocks.append(f"[Context Block {idx}]:\n{t}")
    final_context_str = "\n\n".join(context_blocks)

    print(f"\n--- STAGE 5: FINAL CONTEXT FOR LLM ---")
    if final_context_str:
        print(final_context_str)
    else:
        print("<EMPTY CONTEXT>")

    # Step 6: Groq LLM Generation
    gen_out = generate_answer(question=question, selected_chunks=selected_chunks)
    generated_answer = gen_out.get("answer", "")

    print(f"\n--- STAGE 6: GENERATED ANSWER ---")
    print(generated_answer)

    # Step 7: Grounding & Output Guard
    grounding_res = check_grounding(answer=generated_answer, selected_chunks=selected_chunks)
    og_res = validate_answer(answer=generated_answer, selected_chunks=selected_chunks, question=question)

    print(f"\n--- STAGE 7: GROUNDING & OUTPUT GUARD ---")
    print(f"Grounding Score: {grounding_res.get('grounding_score')} | Grounded: {grounding_res.get('grounded')}")
    print(f"Unsupported Claims: {grounding_res.get('unsupported_claims')}")
    print(f"Output Guard Allowed: {og_res.get('allowed')} | Risk Level: {og_res.get('risk_level')}")

    print("\n" + "=" * 80 + "\n")

    return {
        "doc_id": doc_id,
        "doc_version": doc_version,
        "retrieved_candidates": retrieved_candidates,
        "reranked_results": reranked_results,
        "selected_chunks": selected_chunks,
        "final_context_str": final_context_str,
        "generated_answer": generated_answer,
        "grounding": grounding_res,
        "output_guard": og_res,
    }


if __name__ == "__main__":
    import sys
    doc = sys.argv[1] if len(sys.argv) > 1 else "eval_doc.txt"
    q = sys.argv[2] if len(sys.argv) > 2 else "What is LinguaCorp's revenue?"
    trace_pipeline(doc, q)
