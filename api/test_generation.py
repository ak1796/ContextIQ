import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.generator import generate_answer
from api.pipeline import query_pipeline
from api.main import app
from ingest import get_cache
from retrieval import ingest_and_index_document


class TestGenerationAndPipeline(unittest.TestCase):

    def setUp(self):
        self.cache = get_cache()

    def test_missing_api_key(self):
        """Verify structured failure when GROQ_API_KEY is missing."""
        original_key = os.environ.get("GROQ_API_KEY")
        try:
            os.environ["GROQ_API_KEY"] = ""
            res = generate_answer(
                question="What is CacheLingua?",
                selected_chunks=[{"compressed_text": "CacheLingua compresses context."}],
            )
            self.assertFalse(res["success"])
            self.assertIsNotNone(res["error"])
            self.assertIn("GROQ_API_KEY not configured", res["answer"])
        finally:
            if original_key is not None:
                os.environ["GROQ_API_KEY"] = original_key

    def test_empty_context_handling(self):
        """Verify clean response when no context chunks are provided."""
        res = generate_answer(question="What is AI?", selected_chunks=[])
        self.assertTrue(res["success"])
        self.assertIn("don't have enough information", res["answer"])

    def test_groq_live_generation(self):
        """Live Groq call test if GROQ_API_KEY is available."""
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key or api_key == "your_groq_api_key_here":
            print("\n[SKIP] Groq live test skipped — GROQ_API_KEY not configured.")
            return

        print("\n[LIVE TEST] Executing 1 real Groq LLM API call...")
        res = generate_answer(
            question="How does prompt compression benefit LLMs?",
            selected_chunks=[
                {
                    "chunk_index": 0,
                    "compressed_text": "Prompt compression reduces context size, saving latency and token cost for LLM inference.",
                    "original_text": "Prompt compression reduces context size significantly, which saves both latency and token costs during LLM inference.",
                    "relevance_score": 0.92,
                }
            ],
        )

        print(f"    - Success           : {res['success']}")
        print(f"    - Model             : {res['model']}")
        print(f"    - Prompt Tokens     : {res['prompt_tokens']}")
        print(f"    - Completion Tokens : {res['completion_tokens']}")
        print(f"    - Latency           : {res['generation_latency_ms']} ms")
        print(f"    - Answer Snippet    : {res['answer'][:120]}...")

        self.assertTrue(res["success"])
        self.assertGreater(len(res["answer"]), 0)
        self.assertIsNone(res["error"])

    def test_full_end_to_end_pipeline(self):
        """End-to-end integration test: ingest -> index -> retrieve -> rerank -> budget -> generate."""
        sample_path = os.path.join("sample_docs", "doc1.txt")
        with open(sample_path, "r", encoding="utf-8") as f:
            doc_text = f.read()

        doc_id = "doc1.txt"
        ingest_res = ingest_and_index_document(text=doc_text, doc_id=doc_id, cache=self.cache)
        self.assertGreater(ingest_res["indexed_chunks"], 0)

        # Run pipeline
        out = query_pipeline(
            doc_id=doc_id,
            question="How are cache keys generated for stored document chunks?",
            k=4,
            top_n=2,
            cache=self.cache,
        )

        print("\n[PIPELINE TEST RESULTS]:")
        print(f"    - Document ID       : {out['doc_id']} (v{out['doc_version']})")
        print(f"    - Retrieved Chunks  : {out['retrieved_chunks']}")
        print(f"    - Reranked Chunks   : {out['reranked_chunks']}")
        print(f"    - Selected Chunks   : {out['selected_chunks_count']}")
        print(f"    - Original Tokens   : {out['original_tokens']}")
        print(f"    - Compressed Tokens : {out['compressed_tokens']}")
        print(f"    - Tokens Saved      : {out['tokens_saved']}")
        print(f"    - Compression Ratio : {out['compression_ratio']}")
        print(f"    - Retrieval Latency : {out['retrieval_latency_ms']} ms")
        print(f"    - Rerank Latency    : {out['rerank_latency_ms']} ms")
        print(f"    - Budget Latency    : {out['budget_latency_ms']} ms")
        print(f"    - Gen Latency       : {out['generation_latency_ms']} ms")
        print(f"    - Total Latency     : {out['total_latency_ms']} ms")
        print(f"    - Answer Snippet    : {out['answer'][:150]}...")

        self.assertIn("answer", out)
        self.assertGreaterEqual(out["total_latency_ms"], 0)
        self.assertGreater(out["selected_chunks_count"], 0)

    def test_fastapi_endpoints(self):
        """Test FastAPI /health and /query endpoints."""
        client = TestClient(app)

        # /health
        health_resp = client.get("/health")
        self.assertEqual(health_resp.status_code, 200)
        self.assertEqual(health_resp.json(), {"status": "ok"})

        # /query
        query_payload = {
            "doc_id": "doc1.txt",
            "question": "What methods improve retrieval efficiency?",
            "k": 4,
            "top_n": 2,
        }
        query_resp = client.post("/query", json=query_payload)
        self.assertEqual(query_resp.status_code, 200)
        data = query_resp.json()
        self.assertIn("answer", data)
        self.assertIn("total_latency_ms", data)


if __name__ == "__main__":
    unittest.main()
