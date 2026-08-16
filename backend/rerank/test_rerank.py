import os
import sys
import subprocess

# Ensure root workspace directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingest import get_cache, CACHE_TYPE
from backend.retrieval import ingest_and_index_document, retrieve_top_k
from backend.rerank import rerank, get_reranker_model, retrieve_and_rerank, DEFAULT_RERANKER_MODEL


def run_phase3_test():
    print("=" * 65)
    print("Phase 3: Reranking Layer Test Suite")
    print("=" * 65)

    cache = get_cache()
    cache.clear()
    print(f"[1] Active Cache Backend: {CACHE_TYPE.upper()}")
    print(f"    Reranker Model: {DEFAULT_RERANKER_MODEL}")

    # --- Setup: Phase 1 ingest + Phase 2 indexing ---
    sample_path = os.path.join("sample_docs", "doc1.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        doc1_text = f.read()

    doc_id = "doc1.txt"
    print(f"\n[2] Ingesting & Indexing '{sample_path}' (doc_id: '{doc_id}')")
    ingest_res = ingest_and_index_document(text=doc1_text, doc_id=doc_id, cache=cache)
    print(f"    - Document Version : {ingest_res['doc_version']}")
    print(f"    - Total Chunks     : {ingest_res['total_chunks']}")
    print(f"    - Indexed Chunks   : {ingest_res['indexed_chunks']}")

    # --- Model reuse verification ---
    print(f"\n[3] CrossEncoder Model Singleton Verification")
    model_a = get_reranker_model()
    model_b = get_reranker_model()
    assert model_a is model_b, "CrossEncoder model must be a singleton (same object)"
    print(f"    - get_reranker_model() returned same object: {model_a is model_b} [OK]")

    # --- Main pipeline: 3 questions ---
    questions = [
        "How is artificial intelligence affecting software engineering?",
        "What methods improve retrieval efficiency in modern systems?",
        "How are cache keys generated for stored document chunks?",
    ]

    print("\n[4] Running Full Retrieval + Reranking Pipeline (k=4, top_n=2):")
    for idx, question in enumerate(questions, 1):
        out = retrieve_and_rerank(
            doc_id=doc_id,
            question=question,
            k=4,
            top_n=2,
            cache=cache,
        )

        retrieved = out["retrieved_candidates"]
        reranked = out["results"]
        ret_lat = out["retrieval_latency_ms"]
        rer_lat = out["rerank_latency_ms"]
        tot_lat = out["total_latency_ms"]

        print(f"\n    Q{idx}: \"{question}\"")
        print(f"    Retrieved Candidates ({len(retrieved)}):")
        for r in retrieved:
            print(f"      * Chunk [{r['chunk_index']}] | similarity_score: {r['similarity_score']} | cache_key: {r['cache_key']}")

        print(f"    Reranked Candidates ({len(reranked)}, top_n=2):")
        for r in reranked:
            print(f"      * Chunk [{r['chunk_index']}] | relevance_score: {r['relevance_score']} | cache_key: {r['cache_key']}")

        print(f"    Retrieval Latency  : {ret_lat} ms")
        print(f"    Reranking Latency  : {rer_lat} ms")
        print(f"    Total Latency      : {tot_lat} ms")

        # --- Assertions ---
        # Sorted descending by relevance_score
        scores = [r["relevance_score"] for r in reranked]
        assert scores == sorted(scores, reverse=True), \
            f"Q{idx}: Reranked scores must be sorted descending. Got: {scores}"
        print(f"    - Descending sort assertion PASSED: {scores}")

        # All reranked chunks existed in retrieved candidates
        retrieved_keys = {r["cache_key"] for r in retrieved}
        for r in reranked:
            assert r["cache_key"] in retrieved_keys, \
                f"Reranked chunk cache_key '{r['cache_key']}' not in retrieved candidates!"
        print(f"    - All reranked chunks in retrieved candidates: [OK]")

        # No duplicate cache_keys in reranked results
        reranked_keys = [r["cache_key"] for r in reranked]
        assert len(reranked_keys) == len(set(reranked_keys)), \
            "Duplicate cache_keys found in reranked results!"
        print(f"    - No duplicate cache_keys: [OK]")

        # Metadata preservation
        for r in reranked:
            assert "doc_id" in r and "doc_version" in r and "cache_key" in r, \
                "Required metadata fields missing from reranked chunk!"
            assert r["doc_version"] == ingest_res["doc_version"], \
                f"doc_version mismatch: expected {ingest_res['doc_version']}, got {r['doc_version']}"
        print(f"    - Metadata preservation (doc_id, doc_version, cache_key): [OK]")

    # --- Edge case testing ---
    print("\n[5] Edge Case Handling:")

    # Empty question
    ec1 = rerank(question="", chunks=[{"chunk_index": 0, "compressed_text": "test", "cache_key": "abc"}])
    assert ec1["results"] == [], "Empty question must return empty results"
    print(f"    - Empty question -> empty results: [OK]")

    # Empty chunks
    ec2 = rerank(question="What is AI?", chunks=[])
    assert ec2["results"] == [], "Empty chunks must return empty results"
    print(f"    - Empty chunks -> empty results: [OK]")

    # top_n <= 0 returns all
    chunks_sample = [
        {"chunk_index": 0, "compressed_text": "AI learning software", "cache_key": "k1",
         "doc_id": "doc1", "doc_version": 1, "original_text": "...", "similarity_score": 0.5},
        {"chunk_index": 1, "compressed_text": "cache key hashing", "cache_key": "k2",
         "doc_id": "doc1", "doc_version": 1, "original_text": "...", "similarity_score": 0.4},
    ]
    ec3 = rerank(question="AI?", chunks=chunks_sample, top_n=0)
    assert len(ec3["results"]) == len(chunks_sample), "top_n=0 must return all candidates"
    print(f"    - top_n=0 -> returns all {len(ec3['results'])} chunks: [OK]")

    # top_n > len(chunks) returns all available
    ec4 = rerank(question="AI?", chunks=chunks_sample, top_n=100)
    assert len(ec4["results"]) == len(chunks_sample), "top_n > len(chunks) must return all available"
    print(f"    - top_n > len(chunks) -> returns all {len(ec4['results'])} chunks: [OK]")

    # Full-precision sorting verification (scores sorted before rounding)
    scores_ec4 = [r["relevance_score"] for r in ec4["results"]]
    assert scores_ec4 == sorted(scores_ec4, reverse=True), "Results must be sorted descending"
    print(f"    - Full-precision sort verified: {scores_ec4} [OK]")

    print("\n[SUCCESS] Phase 3 Reranking Tests Passed cleanly!")
    print("=" * 65)


def run_regression_tests():
    print("\n" + "=" * 65)
    print("Phase 1 & Phase 2 Regression Tests")
    print("=" * 65)

    for label, script in [
        ("Phase 1 — Ingest Test", "ingest/test_ingest.py"),
        ("Phase 1 — Cache Backend Test", "ingest/test_cache_backends.py"),
        ("Phase 2 — Retrieval Test", "retrieval/test_retrieval.py"),
    ]:
        print(f"\nRunning: {label} ({script})")
        result = subprocess.run(
            [sys.executable, script],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            # Print just the last few lines to avoid clutter
            lines = result.stdout.strip().splitlines()
            for line in lines[-5:]:
                print(f"  {line}")
            print(f"  RESULT: PASS (exit 0)")
        else:
            print(f"  STDOUT:\n{result.stdout}")
            print(f"  STDERR:\n{result.stderr}")
            print(f"  RESULT: FAIL (exit {result.returncode})")
            sys.exit(1)

    print("\n[SUCCESS] All Phase 1 & Phase 2 Regression Tests Passed!")
    print("=" * 65)


if __name__ == "__main__":
    run_phase3_test()
    run_regression_tests()
