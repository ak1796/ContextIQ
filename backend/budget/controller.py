"""
Calibrated Budget Controller for CacheLingua.

Determines available context token budget based on system limits, question length,
and reserve tokens, then adaptively selects context chunks in descending relevance order.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv  # Ensure dotenv loaded if needed

from backend.budget.token_counter import count_tokens

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Default Configuration Constants
DEFAULT_MAX_CONTEXT_TOKENS = 4000
DEFAULT_MAX_OUTPUT_TOKENS = 800
DEFAULT_BUDGET_RESERVE_TOKENS = 200
ESTIMATED_SYSTEM_PROMPT_TOKENS = 150


def get_budget_config() -> Dict[str, int]:
    """Retrieves current budget configuration from environment variables."""
    return {
        "max_context_tokens": int(os.getenv("MAX_CONTEXT_TOKENS", DEFAULT_MAX_CONTEXT_TOKENS)),
        "max_output_tokens": int(os.getenv("MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS)),
        "budget_reserve_tokens": int(os.getenv("BUDGET_RESERVE_TOKENS", DEFAULT_BUDGET_RESERVE_TOKENS)),
    }


def allocate_context_budget(
    question: str,
    reranked_chunks: List[Dict[str, Any]],
    max_context_tokens: Optional[int] = None,
    reserve_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Adaptively selects candidate chunks within token budget limits.

    1. Calculates prompt overhead = tokens(question) + system prompt reserve.
    2. Calculates available_context_budget = MAX_CONTEXT_TOKENS - prompt_overhead - BUDGET_RESERVE_TOKENS.
    3. Iterates through reranked_chunks in descending relevance order.
    4. Selects chunks until adding the next chunk would exceed available_context_budget.
    5. Calculates exact compression metrics (original_tokens, compressed_tokens, tokens_saved, compression_ratio).

    Returns structured allocation results and timing metrics.
    """
    start_time = time.perf_counter()
    config = get_budget_config()

    max_ctx = max_context_tokens if max_context_tokens is not None else config["max_context_tokens"]
    reserve = reserve_tokens if reserve_tokens is not None else config["budget_reserve_tokens"]

    # Calculate overhead
    question_tokens = count_tokens(question) if question else 0
    prompt_overhead = question_tokens + ESTIMATED_SYSTEM_PROMPT_TOKENS

    available_budget = max(0, max_ctx - prompt_overhead - reserve)

    selected_chunks = []
    accumulated_context_tokens = 0

    # Adaptively select chunks in relevance order
    if reranked_chunks:
        for chunk in reranked_chunks:
            # Use compressed text if available, fallback to original_text
            chunk_text = chunk.get("compressed_text") or chunk.get("original_text") or ""
            chunk_token_count = count_tokens(chunk_text)

            if accumulated_context_tokens + chunk_token_count <= available_budget:
                selected_chunks.append(dict(chunk))
                accumulated_context_tokens += chunk_token_count
            else:
                # Documented default strategy: Stop when the next chunk cannot fit
                break

    # Calculate compression metrics for selected chunks
    total_original_tokens = 0
    total_compressed_tokens = 0

    for chunk in selected_chunks:
        orig_count = chunk.get("token_count_before")
        if orig_count is None:
            orig_text = chunk.get("original_text", "")
            orig_count = count_tokens(orig_text) if orig_text else 0
        total_original_tokens += orig_count

        comp_count = chunk.get("token_count_after")
        if comp_count is None:
            comp_text = chunk.get("compressed_text", "")
            comp_count = count_tokens(comp_text) if comp_text else 0
        total_compressed_tokens += comp_count

    tokens_saved = max(0, total_original_tokens - total_compressed_tokens)
    compression_ratio = (
        round(total_compressed_tokens / total_original_tokens, 4)
        if total_original_tokens > 0
        else 1.0
    )

    budget_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "selected_chunks": selected_chunks,
        "total_context_tokens": accumulated_context_tokens,
        "remaining_budget": max(0, available_budget - accumulated_context_tokens),
        "available_budget": available_budget,
        "chunks_considered": len(reranked_chunks) if reranked_chunks else 0,
        "chunks_selected": len(selected_chunks),
        "original_tokens": total_original_tokens,
        "compressed_tokens": total_compressed_tokens,
        "tokens_saved": tokens_saved,
        "compression_ratio": compression_ratio,
        "budget_latency_ms": budget_latency_ms,
    }
