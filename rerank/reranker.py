import time
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_RERANKER_MODEL_INSTANCE = None
_CURRENT_MODEL_NAME = None
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def get_reranker_model(model_name: str = DEFAULT_RERANKER_MODEL) -> CrossEncoder:
    """
    Returns a singleton instance of the CrossEncoder reranker model.
    Loaded once on CPU and reused across query invocations.
    """
    global _RERANKER_MODEL_INSTANCE, _CURRENT_MODEL_NAME
    if _RERANKER_MODEL_INSTANCE is None or _CURRENT_MODEL_NAME != model_name:
        logger.info(f"Loading CrossEncoder model '{model_name}' on CPU...")
        _RERANKER_MODEL_INSTANCE = CrossEncoder(model_name, device="cpu")
        _CURRENT_MODEL_NAME = model_name
    return _RERANKER_MODEL_INSTANCE


def rerank(
    question: str,
    chunks: List[Dict[str, Any]],
    top_n: int = 5,
    model_name: str = DEFAULT_RERANKER_MODEL,
) -> Dict[str, Any]:
    """
    Reranks candidate chunks retrieved from Phase 2:
    1. Scores pairs of (question, chunk["compressed_text"]) using CrossEncoder.
    2. Sorts candidates descending using full-precision raw CrossEncoder scores.
    3. Rounds relevance_score to 4 decimal places ONLY after sorting for output display.
    4. Preserves all Phase 2 metadata (doc_id, doc_version, chunk_index, cache_key, compressed_text, original_text, similarity_score).
    5. Exposes rerank_latency_ms measured via time.perf_counter().
    """
    start_time = time.perf_counter()

    # Edge cases handling
    if not question or not question.strip() or not chunks:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "results": [],
            "rerank_latency_ms": latency_ms,
        }

    # Determine effective top_n
    if top_n <= 0:
        effective_n = len(chunks)
    else:
        effective_n = min(top_n, len(chunks))

    # Load singleton model
    model = get_reranker_model(model_name)

    # Build sentence pairs for batch scoring
    pairs = [(question, chunk.get("compressed_text", "")) for chunk in chunks]

    # Predict raw scores in a single batch pass
    raw_scores = model.predict(pairs)

    # Combine original chunk dicts with raw_scores for full-precision sorting
    scored_chunks = []
    for idx, chunk in enumerate(chunks):
        raw_score = float(raw_scores[idx]) if hasattr(raw_scores[idx], "item") else float(raw_scores[idx])
        scored_chunks.append((raw_score, chunk))

    # Sort descending using full-precision raw_score to prevent tie/ordering changes
    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    # Select top_n candidates and format score to 4 decimal places ONLY after sorting
    reranked_results = []
    for raw_score, chunk in scored_chunks[:effective_n]:
        res_entry = dict(chunk)
        res_entry["relevance_score"] = round(raw_score, 4)
        reranked_results.append(res_entry)

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "results": reranked_results,
        "rerank_latency_ms": latency_ms,
    }
