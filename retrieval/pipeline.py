from typing import Dict, Any, Optional
from ingest.ingest import ingest_document
from ingest.cache import get_cache, CacheBackend
from retrieval.vector_store import index_chunks


def ingest_and_index_document(
    text: str,
    doc_id: str,
    cache: Optional[CacheBackend] = None,
    rate: float = 0.6,
) -> Dict[str, Any]:
    """
    Pipeline orchestrator for Phase 1 + Phase 2:
    1. Ingests and compresses text via Phase 1 (LLMLingua-2 & Redis/SQLite cache).
    2. Generates sentence-transformers embeddings for chunks.
    3. Indexes vectors and metadata in ChromaDB collection for doc_id.
    """
    if cache is None:
        cache = get_cache()

    # Step 1: Phase 1 Ingest & Cache
    ingest_result = ingest_document(text=text, doc_id=doc_id, cache=cache, rate=rate)

    doc_version = ingest_result["doc_version"]
    records = ingest_result["records"]

    # Step 2: Phase 2 Vector Indexing
    indexed_count = index_chunks(doc_id=doc_id, doc_version=doc_version, chunks=records)

    return {
        "doc_id": doc_id,
        "doc_version": doc_version,
        "total_chunks": ingest_result["total_chunks"],
        "indexed_chunks": indexed_count,
        "cache_keys": ingest_result["cache_keys"],
        "evicted_count": ingest_result["evicted_count"],
    }
