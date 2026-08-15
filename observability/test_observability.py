"""
Tests for Phase 8 Observability: health probing and query analytics.
Uses an isolated in-memory SQLite database path (temp file) for analytics tests.
"""

import os
import tempfile
import pytest

from observability.metrics import record_query, get_summary, get_recent


# ─── Fixtures ─────────────────────────────────────────────── #

@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary analytics database path isolated per test."""
    return str(tmp_path / "test_analytics.db")


def _make_result(
    *,
    doc_id="doc1.txt",
    answer_status="grounded",
    success=True,
    grounding_score=0.85,
    retrieved_chunks=8,
    reranked_chunks=5,
    selected_chunks_count=3,
    original_tokens=600,
    compressed_tokens=400,
    tokens_saved=200,
    compression_ratio=0.67,
    total_latency_ms=1200.0,
    retrieval_latency_ms=300.0,
    rerank_latency_ms=250.0,
    generation_latency_ms=600.0,
    input_guard=None,
    output_guard=None,
) -> dict:
    return {
        "doc_id": doc_id,
        "answer_status": answer_status,
        "success": success,
        "grounding_score": grounding_score,
        "retrieved_chunks": retrieved_chunks,
        "reranked_chunks": reranked_chunks,
        "selected_chunks_count": selected_chunks_count,
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "tokens_saved": tokens_saved,
        "compression_ratio": compression_ratio,
        "total_latency_ms": total_latency_ms,
        "retrieval_latency_ms": retrieval_latency_ms,
        "rerank_latency_ms": rerank_latency_ms,
        "generation_latency_ms": generation_latency_ms,
        "input_guard": input_guard or {"allowed": True, "risk_level": "low", "reason": None},
        "output_guard": output_guard or {"allowed": True, "grounded": True, "grounding_score": 0.85},
    }


# ─── Analytics Recording Tests ────────────────────────────── #

class TestAnalyticsRecording:

    def test_record_and_retrieve(self, tmp_db):
        """A recorded query appears in get_recent."""
        record_query(_make_result(), db_path=tmp_db)
        rows = get_recent(limit=10, db_path=tmp_db)
        assert len(rows) == 1
        assert rows[0]["doc_id"] == "doc1.txt"
        assert rows[0]["answer_status"] == "grounded"
        assert rows[0]["success"] == 1

    def test_empty_analytics_state(self, tmp_db):
        """Empty database returns zeroed summary and empty recent list."""
        summary = get_summary(db_path=tmp_db)
        assert summary["total_queries"] == 0
        assert summary["successful_queries"] == 0
        assert summary["blocked_queries"] == 0
        assert summary["average_latency_ms"] == 0.0

        rows = get_recent(limit=10, db_path=tmp_db)
        assert rows == []

    def test_blocked_query_tracking(self, tmp_db):
        """Blocked queries are counted separately in summary."""
        record_query(_make_result(answer_status="blocked", success=False,
                                  input_guard={"allowed": False, "risk_level": "high", "reason": "injection"}),
                     db_path=tmp_db)
        summary = get_summary(db_path=tmp_db)
        assert summary["blocked_queries"] == 1
        assert summary["successful_queries"] == 0

    def test_insufficient_context_tracking(self, tmp_db):
        """Insufficient-context responses are counted separately."""
        record_query(_make_result(answer_status="insufficient_context", success=True,
                                  grounding_score=1.0, generation_latency_ms=0.0),
                     db_path=tmp_db)
        summary = get_summary(db_path=tmp_db)
        assert summary["insufficient_context_queries"] == 1

    def test_token_metric_calculation(self, tmp_db):
        """tokens_saved and compression_ratio are stored and averaged correctly."""
        record_query(_make_result(tokens_saved=200, compression_ratio=0.67), db_path=tmp_db)
        record_query(_make_result(tokens_saved=300, compression_ratio=0.50), db_path=tmp_db)
        summary = get_summary(db_path=tmp_db)
        assert summary["total_tokens_saved"] == 500
        assert 0.5 < summary["average_compression_ratio"] < 0.7

    def test_latency_metric_calculation(self, tmp_db):
        """Average latency is calculated correctly."""
        record_query(_make_result(total_latency_ms=1000.0), db_path=tmp_db)
        record_query(_make_result(total_latency_ms=2000.0), db_path=tmp_db)
        summary = get_summary(db_path=tmp_db)
        assert summary["average_latency_ms"] == pytest.approx(1500.0, rel=0.01)

    def test_recent_queries_ordering(self, tmp_db):
        """Most recently recorded query appears first in get_recent."""
        record_query(_make_result(doc_id="first.txt"), db_path=tmp_db)
        record_query(_make_result(doc_id="second.txt"), db_path=tmp_db)
        rows = get_recent(limit=10, db_path=tmp_db)
        assert rows[0]["doc_id"] == "second.txt"
        assert rows[1]["doc_id"] == "first.txt"

    def test_recent_queries_limit_respected(self, tmp_db):
        """get_recent respects the limit parameter."""
        for i in range(20):
            record_query(_make_result(doc_id=f"doc{i}.txt"), db_path=tmp_db)
        rows = get_recent(limit=5, db_path=tmp_db)
        assert len(rows) == 5

    def test_record_query_tolerates_missing_fields(self, tmp_db):
        """record_query should not raise even with a minimal/empty dict."""
        record_query({}, db_path=tmp_db)
        rows = get_recent(limit=1, db_path=tmp_db)
        assert len(rows) == 1  # row was inserted with defaults

    def test_summary_mixed_statuses(self, tmp_db):
        """Summary counts multiple answer statuses correctly."""
        record_query(_make_result(answer_status="grounded", success=True), db_path=tmp_db)
        record_query(_make_result(answer_status="grounded", success=True), db_path=tmp_db)
        record_query(_make_result(answer_status="blocked", success=False), db_path=tmp_db)
        record_query(_make_result(answer_status="insufficient_context", success=True), db_path=tmp_db)
        summary = get_summary(db_path=tmp_db)
        assert summary["total_queries"] == 4
        assert summary["successful_queries"] == 3
        assert summary["blocked_queries"] == 1
        assert summary["insufficient_context_queries"] == 1


# ─── Health Endpoint Tests ────────────────────────────────── #

class TestSystemHealth:

    def test_health_returns_required_fields(self):
        """get_system_health always returns the required response structure."""
        from observability.health import get_system_health
        result = get_system_health()
        assert "status" in result
        assert "backend" in result
        assert "redis" in result
        assert "vector_store" in result
        assert "llm" in result
        assert "documents" in result
        assert "timestamp" in result

    def test_health_backend_always_true(self):
        """backend field is always True (the API is running if this runs)."""
        from observability.health import get_system_health
        result = get_system_health()
        assert result["backend"] is True

    def test_health_status_is_string(self):
        """status is a string: 'healthy' or 'degraded'."""
        from observability.health import get_system_health
        result = get_system_health()
        assert result["status"] in ("healthy", "degraded")

    def test_health_documents_is_int(self):
        """documents count is a non-negative integer."""
        from observability.health import get_system_health
        result = get_system_health()
        assert isinstance(result["documents"], int)
        assert result["documents"] >= 0

    def test_health_never_raises(self):
        """get_system_health must not raise under any circumstances."""
        from observability.health import get_system_health
        try:
            result = get_system_health()
            assert isinstance(result, dict)
        except Exception as exc:
            pytest.fail(f"get_system_health raised an exception: {exc}")


# ─── FastAPI Endpoint Integration Tests ────────────────────── #

class TestObservabilityEndpoints:

    def test_system_health_endpoint(self):
        """GET /system/health returns 200 with correct structure."""
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        resp = client.get("/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "backend" in data
        assert "redis" in data

    def test_analytics_summary_endpoint_empty(self):
        """GET /analytics/summary returns 200 with zeroed data (or real data)."""
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        resp = client.get("/analytics/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_queries" in data
        assert "average_latency_ms" in data

    def test_analytics_recent_endpoint_empty(self):
        """GET /analytics/recent returns 200 with a 'queries' list."""
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        resp = client.get("/analytics/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert "queries" in data
        assert isinstance(data["queries"], list)
