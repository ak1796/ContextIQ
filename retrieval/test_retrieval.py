import os
import sys

# Ensure root workspace directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingest import get_cache, CACHE_TYPE
from retrieval import (
    ingest_and_index_document,
    retrieve_top_k,
    sanitize_collection_name,
)


def run_retrieval_test():
    print("=" * 65)
    print("Phase 2: Retrieval Layer Test Suite")
    print("=" * 65)

    cache = get_cache()
    cache.clear()

    print(f"[1] Active Cache Backend: {CACHE_TYPE.upper()}")

    # 1. Load sample_docs/doc1.txt
    sample_path = os.path.join("sample_docs", "doc1.txt")
    if not os.path.exists(sample_path):
        os.makedirs("sample_docs", exist_ok=True)
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(
                "Artificial intelligence and machine learning are revolutionizing software development.\n"
                "Modern systems utilize document compression and caching layers for efficient retrieval.\n"
                "This sample document demonstrates prompt compression using LLMLingua-2.\n"
                "Cache keys are deterministically generated based on content hashes and document IDs.\n"
            )

    with open(sample_path, "r", encoding="utf-8") as f:
        doc1_text = f.read()

    doc_id = "doc1.txt"
    print(f"\n[2] Ingesting & Vector Indexing file: '{sample_path}' (doc_id: '{doc_id}')")

    ingest_res = ingest_and_index_document(text=doc1_text, doc_id=doc_id, cache=cache)

    print(f"    - Document Version: {ingest_res['doc_version']}")
    print(f"    - Total Chunks:     {ingest_res['total_chunks']}")
    print(f"    - Indexed Chunks:   {ingest_res['indexed_chunks']}")
    print(f"    - Chroma Collection:{sanitize_collection_name(doc_id)}")

    # 2. Run at least 3 test questions
    questions = [
        "How is artificial intelligence affecting software engineering?",
        "What methods improve retrieval efficiency in modern systems?",
        "How are cache keys generated for stored document chunks?",
    ]

    print("\n[3] Executing Top-K Semantic Retrievals:")
    for idx, q in enumerate(questions, 1):
        ret_out = retrieve_top_k(doc_id=doc_id, question=q, k=2, cache=cache)
        results = ret_out["results"]
        latency_ms = ret_out["retrieval_latency_ms"]

        print(f"\n    Q{idx}: \"{q}\"")
        print(f"    - Retrieval Latency: {latency_ms} ms")
        print(f"    - Matches Found: {len(results)}")

        for res in results:
            chunk_idx = res["chunk_index"]
            score = res["similarity_score"]
            c_key = res["cache_key"]
            comp_txt = res["compressed_text"]
            orig_txt = res["original_text"]

            print(f"      * Chunk [{chunk_idx}] | Similarity: {score} | Cache Key: {c_key}")
            print(f"        Original:   {orig_txt}")
            print(f"        Compressed: {comp_txt}")

            # Verify cache_key exists in Phase 1 Redis/SQLite cache
            cached_data = cache.get(c_key)
            assert cached_data is not None, f"Cache key '{c_key}' MUST exist in cache backend!"
            assert cached_data["compressed_text"] == comp_txt, "Returned text MUST match cache entry!"
            assert res["doc_version"] == ingest_res["doc_version"], "Returned chunk MUST match current doc_version!"

    # 3. Test re-ingestion and version filtering
    print(f"\n[4] Re-ingesting modified document content (doc_id: '{doc_id}')")
    modified_text = doc1_text + "\nVector search layer uses sentence-transformers all-MiniLM-L6-v2 for semantic embeddings."

    reingest_res = ingest_and_index_document(text=modified_text, doc_id=doc_id, cache=cache)

    print(f"    - New Document Version: {reingest_res['doc_version']} (v1 -> v2)")
    print(f"    - Total Chunks (v2):    {reingest_res['total_chunks']}")
    print(f"    - Indexed Chunks (v2):  {reingest_res['indexed_chunks']}")

    # 4. Query again and assert strictly current doc_version=2 results returned
    q_ver = "What embedding model is used for semantic embeddings?"
    ver_out = retrieve_top_k(doc_id=doc_id, question=q_ver, k=5, cache=cache)
    ver_results = ver_out["results"]

    print(f"\n[5] Version Filtering Verification (Query against doc_version = {reingest_res['doc_version']}):")
    print(f"    Q: \"{q_ver}\"")
    print(f"    - Retrieval Latency: {ver_out['retrieval_latency_ms']} ms")
    
    for r in ver_results:
        print(f"      * Chunk [{r['chunk_index']}] | Version: {r['doc_version']} | Key: {r['cache_key']}")
        assert r["doc_version"] == 2, f"Expected doc_version 2, got stale version {r['doc_version']}!"

    print("\n[SUCCESS] Phase 2 Retrieval Layer Tests Passed cleanly!")
    print("=" * 65)


if __name__ == "__main__":
    run_retrieval_test()
