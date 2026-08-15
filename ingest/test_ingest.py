import os
import sys

# Ensure root workspace directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingest import (
    compress_document,
    ingest_document,
    reingest_document,
    get_cache,
    CACHE_TYPE,
)


def run_test():
    print("=" * 60)
    print("Phase 1 — Stage 0: Ingest & Cache Test Suite")
    print("=" * 60)

    cache = get_cache()
    cache.clear()
    print(f"[1] Active Cache Backend: {CACHE_TYPE.upper()}")

    # 1. Check/Load sample_docs/doc1.txt
    sample_path = os.path.join("sample_docs", "doc1.txt")
    if not os.path.exists(sample_path):
        os.makedirs("sample_docs", exist_ok=True)
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(
                "Artificial intelligence is transforming prompt context engineering.\n"
                "Document compression reduces token costs effectively.\n"
                "LLMLingua-2 provides task-agnostic sentence compression.\n"
            )

    with open(sample_path, "r", encoding="utf-8") as f:
        doc1_text = f.read()

    doc_id = "doc1.txt"
    print(f"\n[2] Ingesting original file: {sample_path} (doc_id: '{doc_id}')")
    
    result1 = ingest_document(text=doc1_text, doc_id=doc_id, cache=cache)
    
    print(f"    - Document Version: {result1['doc_version']}")
    print(f"    - Total Chunks: {result1['total_chunks']}")
    print("    - Generated Cache Keys:")
    for idx, key in enumerate(result1["cache_keys"]):
        rec = result1["records"][idx]["entry"]
        print(f"      Key [{idx}]: {key} | Tokens: {rec.get('token_count_before')} -> {rec.get('token_count_after')}")
        print(f"        Original:   {rec.get('original_text')}")
        print(f"        Compressed: {rec.get('compressed_text')}")
        print(f"        Embedding:  {rec.get('embedding')}")
        print(f"        Created At: {rec.get('created_at')}")

    # 2. Modify document content slightly and re-ingest
    modified_text = doc1_text + "\nRe-ingesting this document with updated content triggers key generation."
    print(f"\n[3] Re-ingesting modified document content (doc_id: '{doc_id}')")

    result2 = ingest_document(text=modified_text, doc_id=doc_id, cache=cache)

    print(f"    - Document Version: {result2['doc_version']} (Incremented)")
    print(f"    - Total Chunks: {result2['total_chunks']}")
    print("    - Generated Cache Keys (Modified Document):")
    for idx, key in enumerate(result2["cache_keys"]):
        print(f"      Key [{idx}]: {key}")


    # 3. Assertions
    old_keys = set(result1["cache_keys"])
    new_keys = set(result2["cache_keys"])

    print("\n[4] Cache Invalidation & Versioning Verification:")
    print(f"    - Old Cache Keys Count: {len(old_keys)}")
    print(f"    - New Cache Keys Count: {len(new_keys)}")
    
    # Check that new chunk key was added
    newly_added_keys = new_keys - old_keys
    print(f"    - Newly Generated Keys on Modification: {list(newly_added_keys)}")

    assert result2["doc_version"] > result1["doc_version"], "Doc version must increment on re-ingestion!"
    assert len(newly_added_keys) > 0, "Modified document must generate new cache key(s)!"
    
    print("\n[SUCCESS] Phase 1 Ingest & Cache Test Passed cleanly!")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
