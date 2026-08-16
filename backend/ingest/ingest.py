from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.ingest.compressor import compress_document
from backend.ingest.cache import get_cache, compute_cache_key, CacheBackend, DEFAULT_MAX_CACHE_SIZE
from backend.retrieval.hybrid import save_tabular_dataframe


def ingest_document(
    text: str,
    doc_id: str,
    cache: Optional[CacheBackend] = None,
    max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
    rate: float = 0.6,
) -> Dict[str, Any]:
    """
    Ingests a document string with doc_id:
    1. Determines doc_version (increments version if doc_id was previously ingested).
    2. Saves raw DataFrame to tabular store if CSV.
    3. Runs LLMLingua-2 compression on text at the sentence level.
    4. Computes cache key = hash(doc_id + chunk_text + chunk_index).
    5. Checks cache / populates cache entries storing compressed_text, original_text, doc_version,
       chunk_index, embedding (null for now), created_at.
    6. Performs LRU eviction check if cache size exceeds max_cache_size.
    """
    if cache is None:
        cache = get_cache()

    if doc_id.lower().endswith(".csv") or "," in text.splitlines()[0] if text else False:
        try:
            save_tabular_dataframe(doc_id, text)
        except Exception:
            pass

    # Register version: 1 on initial ingest, incremented on re-ingest of same doc_id
    doc_version = cache.register_or_increment_doc_version(doc_id)

    compressed_chunks = compress_document(text, doc_id, rate=rate)


    cache_records = []
    generated_keys = []

    for chunk in compressed_chunks:
        chunk_idx = chunk["chunk_index"]
        original_text = chunk["original_text"]
        compressed_text = chunk["compressed_text"]

        # Cache key format: sha256(doc_id + chunk_text + chunk_index)[:16]
        cache_key = compute_cache_key(doc_id, original_text, chunk_idx)
        generated_keys.append(cache_key)

        cached_entry = cache.get(cache_key)
        if cached_entry:
            cache_records.append({
                "cache_key": cache_key,
                "hit": True,
                "entry": cached_entry,
            })
        else:
            entry = {
                "doc_id": doc_id,
                "compressed_text": compressed_text,
                "original_text": original_text,
                "doc_version": doc_version,
                "chunk_index": chunk_idx,
                "embedding": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "token_count_before": chunk["token_count_before"],
                "token_count_after": chunk["token_count_after"],
            }
            cache.set(cache_key, entry)
            cache_records.append({
                "cache_key": cache_key,
                "hit": False,
                "entry": entry,
            })

    # Trigger LRU eviction check if cache size exceeds max_cache_size
    evicted_count = cache.evict_lru(max_cache_size)

    return {
        "doc_id": doc_id,
        "doc_version": doc_version,
        "total_chunks": len(compressed_chunks),
        "cache_keys": generated_keys,
        "records": cache_records,
        "evicted_count": evicted_count,
    }



def reingest_document(
    text: str,
    doc_id: str,
    cache: Optional[CacheBackend] = None,
    max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
    rate: float = 0.6,
) -> Dict[str, Any]:
    """
    Re-ingest helper: explicitly increments doc_version for doc_id, compresses,
    and caches new content without synchronously deleting old keys.
    """
    if cache is None:
        cache = get_cache()

    if doc_id.lower().endswith(".csv") or (text and "," in text.splitlines()[0]):
        try:
            save_tabular_dataframe(doc_id, text)
        except Exception:
            pass

    new_version = cache.increment_doc_version(doc_id)
    compressed_chunks = compress_document(text, doc_id, rate=rate)

    cache_records = []
    generated_keys = []

    for chunk in compressed_chunks:
        chunk_idx = chunk["chunk_index"]
        original_text = chunk["original_text"]
        compressed_text = chunk["compressed_text"]

        cache_key = compute_cache_key(doc_id, original_text, chunk_idx)
        generated_keys.append(cache_key)

        entry = {
            "doc_id": doc_id,
            "compressed_text": compressed_text,
            "original_text": original_text,
            "doc_version": new_version,
            "chunk_index": chunk_idx,
            "embedding": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "token_count_before": chunk["token_count_before"],
            "token_count_after": chunk["token_count_after"],
        }
        cache.set(cache_key, entry)
        cache_records.append({
            "cache_key": cache_key,
            "hit": False,
            "entry": entry,
        })

    evicted_count = cache.evict_lru(max_cache_size)

    return {
        "doc_id": doc_id,
        "doc_version": new_version,
        "total_chunks": len(compressed_chunks),
        "cache_keys": generated_keys,
        "records": cache_records,
        "evicted_count": evicted_count,
    }
