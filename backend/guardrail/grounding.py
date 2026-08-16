"""
Grounding Verification Module for ContextIQ.

Combines key-entity/fact verification with sentence-level semantic embedding
similarity (`all-MiniLM-L6-v2`) to accurately verify answer groundedness without
rejecting valid answers that reference record labels or headings.
"""

import re
import math
import logging
from typing import List, Dict, Any
import numpy as np

from backend.retrieval.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

# Grounding Threshold Constants
THRESHOLD_DIRECTLY_SUPPORTED = 0.65
THRESHOLD_PARTIALLY_SUPPORTED = 0.40
GROUNDING_PASS_THRESHOLD = 0.60
GROUNDING_PARTIAL_THRESHOLD = 0.35

_NLI_MODEL_INSTANCE = None
DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-small"


def get_nli_grounding_model(model_name: str = DEFAULT_NLI_MODEL):
    """
    Returns a singleton instance of the NLI grounding model.
    Loaded once and reused across invocations on CPU.
    """
    global _NLI_MODEL_INSTANCE
    if _NLI_MODEL_INSTANCE is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading NLI grounding model '{model_name}' on CPU...")
            _NLI_MODEL_INSTANCE = CrossEncoder(model_name, device="cpu")
            print(f"[STARTUP] Loaded {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load NLI grounding model '{model_name}': {e}")
            _NLI_MODEL_INSTANCE = False
    return _NLI_MODEL_INSTANCE


def _split_into_sentences(text: str) -> List[str]:
    """Splits raw text into clean non-empty sentences."""
    if not text:
        return []
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 3]
    return sentences if sentences else ([text.strip()] if text.strip() else [])


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Computes cosine similarity between two 1D numpy vectors."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def _extract_key_tokens(text: str) -> set:
    """Extracts numbers, proper nouns, and key alphanumeric terms."""
    # Find numbers and words with 3+ characters
    words = re.findall(r"\b[A-Za-z0-9_-]{3,}\b", text.lower())
    # Exclude common stop words
    stopwords = {"the", "and", "is", "in", "was", "for", "with", "that", "this", "from", "are", "been", "have", "has", "stated", "record", "according", "context"}
    return {w for w in words if w not in stopwords}


def check_grounding(
    answer: str,
    selected_chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Determines whether the generated answer is supported by selected context chunks.
    Combines embedding semantic similarity with exact entity key-fact verification.
    """
    if not answer or not answer.strip():
        return {
            "grounded": False,
            "grounding_score": 0.0,
            "unsupported_claims": ["Answer is empty."],
            "method": "hybrid_fact_verification",
        }

    # Check for explicit fallback / insufficient context answer phrases
    lowered_ans = answer.lower()
    if "does not contain sufficient information" in lowered_ans or "don't have enough information" in lowered_ans:
        return {
            "grounded": True,
            "grounding_score": 1.0,
            "unsupported_claims": [],
            "method": "insufficient_context_acknowledgment",
        }

    if not selected_chunks:
        return {
            "grounded": False,
            "grounding_score": 0.0,
            "unsupported_claims": [answer],
            "method": "hybrid_fact_verification",
        }

    answer_sentences = _split_into_sentences(answer)
    if not answer_sentences:
        return {
            "grounded": True,
            "grounding_score": 1.0,
            "unsupported_claims": [],
            "method": "hybrid_fact_verification",
        }

    # Gather full context text
    context_texts = []
    context_sentences = []
    for chunk in selected_chunks:
        t = chunk.get("compressed_text") or chunk.get("original_text") or ""
        if t:
            context_texts.append(t)
            context_sentences.extend(_split_into_sentences(t))

    full_context_str = " ".join(context_texts).lower()
    if not full_context_str.strip():
        return {
            "grounded": False,
            "grounding_score": 0.0,
            "unsupported_claims": answer_sentences,
            "method": "hybrid_fact_verification",
        }

    # Encode using singleton embedding model
    model = get_embedding_model()
    ans_embeddings = model.encode(answer_sentences, convert_to_numpy=True)
    ctx_embeddings = model.encode(context_sentences, convert_to_numpy=True) if context_sentences else []

    unsupported_claims = []
    support_scores = []

    for idx, ans_sent in enumerate(answer_sentences):
        ans_vec = ans_embeddings[idx]
        
        # 1. Calculate semantic cosine similarity
        sim_score = max([_cosine_similarity(ans_vec, c_vec) for c_vec in ctx_embeddings]) if len(ctx_embeddings) > 0 else 0.0

        # 2. Extract key entity tokens from answer sentence
        key_tokens = _extract_key_tokens(ans_sent)
        if key_tokens:
            matched_tokens = {t for t in key_tokens if t in full_context_str}
            token_recall = len(matched_tokens) / len(key_tokens)
        else:
            token_recall = 1.0

        # Combine semantic similarity and entity recall
        effective_score = max(sim_score, token_recall)

        if effective_score >= THRESHOLD_DIRECTLY_SUPPORTED or (sim_score >= 0.45 and token_recall >= 0.75):
            support_scores.append(1.0)
        elif effective_score >= THRESHOLD_PARTIALLY_SUPPORTED:
            support_scores.append(0.5)
        else:
            support_scores.append(0.0)
            unsupported_claims.append(ans_sent)

    overall_score = round(float(np.mean(support_scores)), 4) if support_scores else 0.0

    if overall_score >= GROUNDING_PASS_THRESHOLD:
        grounded_status = True
    elif overall_score >= GROUNDING_PARTIAL_THRESHOLD:
        grounded_status = "partial"
    else:
        grounded_status = False

    return {
        "grounded": grounded_status,
        "grounding_score": overall_score,
        "unsupported_claims": unsupported_claims,
        "method": "hybrid_fact_verification",
    }
