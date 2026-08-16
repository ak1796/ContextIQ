import time
import logging
from typing import List, Dict, Any, Optional
from backend.ingest.cache import get_cache, CacheBackend
from backend.retrieval.embeddings import embed_text
from backend.retrieval.vector_store import get_collection, sanitize_collection_name, get_chroma_client

logger = logging.getLogger(__name__)


def retrieve_top_k(
    doc_id: str,
    question: str,
    k: int = 10,
    cache: Optional[CacheBackend] = None,
) -> Dict[str, Any]:
    """
    Retrieves top-k relevant chunks for a question against doc_id:
    1. Embeds question with sentence-transformers (all-MiniLM-L6-v2).
    2. Queries ChromaDB filtering by current doc_version (where={"doc_version": current_version}).
    3. Retrieves cache_key for matches and looks up full original/compressed text from Phase 1 cache.
    4. Measures and exposes retrieval_latency_ms using time.perf_counter().
    Handles empty questions, unknown doc_id, empty collection, and k > total chunks cleanly without crashing.
    """
    start_time = time.perf_counter()

    if cache is None:
        cache = get_cache()

    # Empty / Invalid cases handling
    if not doc_id or not question or not question.strip():
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "results": [],
            "retrieval_latency_ms": latency_ms,
            "doc_id": doc_id,
            "doc_version": 1,
        }

    # Get current version from Phase 1 cache
    current_version = cache.get_doc_version(doc_id)

    # Check if collection exists in ChromaDB
    client = get_chroma_client()
    coll_name = sanitize_collection_name(doc_id)
    
    try:
        existing_colls = [c.name for c in client.list_collections()]
        if coll_name not in existing_colls:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "results": [],
                "retrieval_latency_ms": latency_ms,
                "doc_id": doc_id,
                "doc_version": current_version,
            }
        
        collection = client.get_collection(coll_name)
    except Exception as err:
        logger.warning(f"Chroma collection lookup error for '{doc_id}': {err}")
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "results": [],
            "retrieval_latency_ms": latency_ms,
            "doc_id": doc_id,
            "doc_version": current_version,
        }

    # Check collection count
    total_count = collection.count()
    if total_count == 0:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "results": [],
            "retrieval_latency_ms": latency_ms,
            "doc_id": doc_id,
            "doc_version": current_version,
        }

    # Adjust k if larger than total count
    effective_k = min(k, total_count)

    # Embed query
    query_embedding = embed_text(question)

    # Query ChromaDB filtering strictly by current doc_version
    try:
        query_res = collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_k,
            where={"doc_version": int(current_version)},
        )
    except Exception as query_err:
        logger.warning(f"Error querying ChromaDB collection '{coll_name}': {query_err}")
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "results": [],
            "retrieval_latency_ms": latency_ms,
            "doc_id": doc_id,
            "doc_version": current_version,
        }

    results = []
    if query_res and "metadatas" in query_res and query_res["metadatas"]:
        metadatas = query_res["metadatas"][0]
        distances = query_res.get("distances", [[]])[0]
        documents = query_res.get("documents", [[]])[0]

        for i, meta in enumerate(metadatas):
            cache_key = meta.get("cache_key")
            chunk_index = meta.get("chunk_index")
            doc_ver = meta.get("doc_version", current_version)
            dist = distances[i] if i < len(distances) else 0.0
            
            # Cosine similarity score from distance
            similarity_score = round(max(0.0, 1.0 - float(dist)), 4)

            # Perform Redis/SQLite lookup for cache_key
            cached_entry = cache.get(cache_key) if cache_key else None

            if cached_entry:
                compressed_txt = cached_entry.get("compressed_text", "")
                original_txt = cached_entry.get("original_text", "")
            else:
                # Fallback to stored document text if cache key expired
                compressed_txt = documents[i] if i < len(documents) else ""
                original_txt = compressed_txt

            results.append({
                "doc_id": doc_id,
                "doc_version": doc_ver,
                "chunk_index": chunk_index,
                "cache_key": cache_key,
                "compressed_text": compressed_txt,
                "original_text": original_txt,
                "similarity_score": similarity_score,
            })

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "results": results,
        "retrieval_latency_ms": latency_ms,
        "doc_id": doc_id,
        "doc_version": current_version,
    }
