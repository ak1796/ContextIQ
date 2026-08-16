import os
import sys
import unittest

# Ensure root workspace directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.budget.token_counter import count_tokens, count_messages_tokens
from backend.budget.controller import allocate_context_budget, get_budget_config


class TestBudgetController(unittest.TestCase):

    def test_token_counter_basic(self):
        self.assertEqual(count_tokens(""), 0)
        self.assertGreater(count_tokens("Hello world, this is a test string for token estimation."), 0)

        # Chat messages token counting
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is AI?"},
        ]
        msg_tokens = count_messages_tokens(messages)
        self.assertGreater(msg_tokens, count_tokens("You are a helpful assistant.") + count_tokens("What is AI?"))

    def test_budget_capacity_limit(self):
        """Verify controller never exceeds max_context_tokens."""
        # Create 5 synthetic chunks with known token sizes
        # e.g., words approx ~1 token each
        chunks = [
            {
                "chunk_index": 0,
                "relevance_score": 0.95,
                "compressed_text": "word " * 700,
                "original_text": "original word " * 1000,
                "token_count_before": 1000,
                "token_count_after": 700,
                "cache_key": "k0",
            },
            {
                "chunk_index": 1,
                "relevance_score": 0.85,
                "compressed_text": "word " * 650,
                "original_text": "original word " * 950,
                "token_count_before": 950,
                "token_count_after": 650,
                "cache_key": "k1",
            },
            {
                "chunk_index": 2,
                "relevance_score": 0.75,
                "compressed_text": "word " * 600,
                "original_text": "original word " * 900,
                "token_count_before": 900,
                "token_count_after": 600,
                "cache_key": "k2",
            },
            {
                "chunk_index": 3,
                "relevance_score": 0.65,
                "compressed_text": "word " * 550,
                "original_text": "original word " * 800,
                "token_count_before": 800,
                "token_count_after": 550,
                "cache_key": "k3",
            },
            {
                "chunk_index": 4,
                "relevance_score": 0.55,
                "compressed_text": "word " * 500,
                "original_text": "original word " * 700,
                "token_count_before": 700,
                "token_count_after": 500,
                "cache_key": "k4",
            },
        ]

        # Allocate budget with constrained max_context_tokens = 2000, reserve = 100
        result = allocate_context_budget(
            question="What is the summary?",
            reranked_chunks=chunks,
            max_context_tokens=2000,
            reserve_tokens=100,
        )

        selected = result["selected_chunks"]
        total_tokens = result["total_context_tokens"]
        avail_budget = result["available_budget"]

        # Ensure total tokens <= available budget
        self.assertLessEqual(total_tokens, avail_budget)
        # Ensure chunks were selected in order until limit reached
        self.assertGreater(len(selected), 0)
        self.assertLess(len(selected), len(chunks))

    def test_ranking_preservation(self):
        """Verify selected chunks preserve reranker relevance ordering."""
        chunks = [
            {"chunk_index": 1, "relevance_score": 0.90, "compressed_text": "chunk high rel", "cache_key": "a"},
            {"chunk_index": 0, "relevance_score": 0.70, "compressed_text": "chunk med rel", "cache_key": "b"},
            {"chunk_index": 2, "relevance_score": 0.40, "compressed_text": "chunk low rel", "cache_key": "c"},
        ]

        result = allocate_context_budget(
            question="Test question",
            reranked_chunks=chunks,
            max_context_tokens=4000,
            reserve_tokens=100,
        )

        selected = result["selected_chunks"]
        scores = [c["relevance_score"] for c in selected]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_token_accounting(self):
        """Verify tokens_saved = original_tokens - compressed_tokens."""
        chunks = [
            {
                "chunk_index": 0,
                "compressed_text": "Compressed text content",
                "original_text": "This is much longer original text content before LLMLingua compression",
                "token_count_before": 100,
                "token_count_after": 30,
                "relevance_score": 0.9,
            }
        ]

        result = allocate_context_budget(
            question="Question",
            reranked_chunks=chunks,
        )

        self.assertEqual(result["original_tokens"], 100)
        self.assertEqual(result["compressed_tokens"], 30)
        self.assertEqual(result["tokens_saved"], 70)
        self.assertEqual(result["compression_ratio"], 0.3)

    def test_empty_context_and_question(self):
        """Verify clean handling of empty context or question."""
        res1 = allocate_context_budget(question="", reranked_chunks=[])
        self.assertEqual(res1["chunks_selected"], 0)
        self.assertEqual(res1["selected_chunks"], [])

        res2 = allocate_context_budget(question="Any question?", reranked_chunks=[])
        self.assertEqual(res2["chunks_selected"], 0)
        self.assertEqual(res2["selected_chunks"], [])


if __name__ == "__main__":
    unittest.main()
