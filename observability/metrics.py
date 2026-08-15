"""
Query Analytics Store — Phase 8.

Persists lightweight, safe query metrics to a local SQLite database (analytics.db).
Bounded to MAX_RECORDS rows — oldest records are pruned automatically on insert.

PRIVACY / SECURITY:
- Question text is NOT stored.
- API keys, env vars, system prompts, and stack traces are NOT stored.
- Only numeric metrics and safe categorical fields are persisted.
"""

import os
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "analytics.db")
MAX_RECORDS = 1000

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS query_analytics (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT    NOT NULL,
    doc_id                TEXT,
    answer_status         TEXT,
    success               INTEGER,
    grounding_score       REAL,
    retrieved_chunks      INTEGER,
    reranked_chunks       INTEGER,
    selected_chunks_count INTEGER,
    original_tokens       INTEGER,
    compressed_tokens     INTEGER,
    tokens_saved          INTEGER,
    compression_ratio     REAL,
    total_latency_ms      REAL,
    retrieval_latency_ms  REAL,
    rerank_latency_ms     REAL,
    generation_latency_ms REAL,
    input_guard_status    TEXT,
    output_guard_status   TEXT
);
"""

_PRUNE_SQL = """
DELETE FROM query_analytics
WHERE id NOT IN (
    SELECT id FROM query_analytics
    ORDER BY id DESC
    LIMIT ?
);
"""


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or _DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    return conn


def record_query(result: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """
    Persist safe query metrics extracted from a pipeline result dict.
    Silently swallows all errors — must never block or crash the API.
    """
    try:
        # Extract input/output guard statuses safely
        input_guard = result.get("input_guard") or {}
        output_guard = result.get("output_guard") or {}

        input_guard_status = "allowed" if input_guard.get("allowed", True) else "blocked"
        output_guard_status = (
            "allowed" if output_guard.get("allowed", True) else "blocked"
        ) if output_guard else "n/a"

        row = (
            datetime.now(timezone.utc).isoformat(),
            str(result.get("doc_id", ""))[:128],            # bounded string
            str(result.get("answer_status", "unknown"))[:64],
            int(bool(result.get("success", False))),
            float(result.get("grounding_score") or 0.0),
            int(result.get("retrieved_chunks") or 0),
            int(result.get("reranked_chunks") or 0),
            int(result.get("selected_chunks_count") or 0),
            int(result.get("original_tokens") or 0),
            int(result.get("compressed_tokens") or 0),
            int(result.get("tokens_saved") or 0),
            float(result.get("compression_ratio") or 1.0),
            float(result.get("total_latency_ms") or 0.0),
            float(result.get("retrieval_latency_ms") or 0.0),
            float(result.get("rerank_latency_ms") or 0.0),
            float(result.get("generation_latency_ms") or 0.0),
            input_guard_status[:32],
            output_guard_status[:32],
        )

        conn = _get_connection(db_path)
        with conn:
            conn.execute(
                """
                INSERT INTO query_analytics (
                    timestamp, doc_id, answer_status, success,
                    grounding_score, retrieved_chunks, reranked_chunks,
                    selected_chunks_count, original_tokens, compressed_tokens,
                    tokens_saved, compression_ratio, total_latency_ms,
                    retrieval_latency_ms, rerank_latency_ms, generation_latency_ms,
                    input_guard_status, output_guard_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row,
            )
            # Prune oldest rows beyond MAX_RECORDS
            conn.execute(_PRUNE_SQL, (MAX_RECORDS,))
        conn.close()

    except Exception as exc:
        logger.warning("Analytics record_query failed silently: %s", exc)


def get_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Return aggregated analytics metrics across all stored queries."""
    try:
        conn = _get_connection(db_path)
        row = conn.execute(
            """
            SELECT
                COUNT(*)                                        AS total_queries,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)  AS successful_queries,
                SUM(CASE WHEN answer_status = 'blocked' THEN 1 ELSE 0 END) AS blocked_queries,
                SUM(CASE WHEN answer_status = 'insufficient_context' THEN 1 ELSE 0 END) AS insufficient_context_queries,
                ROUND(AVG(total_latency_ms), 2)                AS average_latency_ms,
                ROUND(AVG(retrieval_latency_ms), 2)            AS average_retrieval_latency_ms,
                ROUND(AVG(rerank_latency_ms), 2)               AS average_rerank_latency_ms,
                ROUND(AVG(generation_latency_ms), 2)           AS average_generation_latency_ms,
                ROUND(AVG(grounding_score), 4)                 AS average_grounding_score,
                ROUND(AVG(compression_ratio), 4)               AS average_compression_ratio,
                SUM(tokens_saved)                              AS total_tokens_saved,
                ROUND(AVG(retrieved_chunks), 2)                AS average_retrieved_chunks,
                ROUND(AVG(selected_chunks_count), 2)           AS average_selected_chunks,
                SUM(CASE WHEN grounding_score >= 0.5 THEN 1 ELSE 0 END) AS grounded_count
            FROM query_analytics
            """
        ).fetchone()
        conn.close()

        total = int(row["total_queries"] or 0)
        grounded_count = int(row["grounded_count"] or 0)
        grounded_pct = round(grounded_count / total * 100, 1) if total > 0 else 0.0

        return {
            "total_queries": total,
            "successful_queries": int(row["successful_queries"] or 0),
            "blocked_queries": int(row["blocked_queries"] or 0),
            "insufficient_context_queries": int(row["insufficient_context_queries"] or 0),
            "average_latency_ms": float(row["average_latency_ms"] or 0.0),
            "average_retrieval_latency_ms": float(row["average_retrieval_latency_ms"] or 0.0),
            "average_rerank_latency_ms": float(row["average_rerank_latency_ms"] or 0.0),
            "average_generation_latency_ms": float(row["average_generation_latency_ms"] or 0.0),
            "average_grounding_score": float(row["average_grounding_score"] or 0.0),
            "grounded_response_pct": grounded_pct,
            "average_compression_ratio": float(row["average_compression_ratio"] or 1.0),
            "total_tokens_saved": int(row["total_tokens_saved"] or 0),
            "average_retrieved_chunks": float(row["average_retrieved_chunks"] or 0.0),
            "average_selected_chunks": float(row["average_selected_chunks"] or 0.0),
        }
    except Exception as exc:
        logger.warning("Analytics get_summary failed: %s", exc)
        return {
            "total_queries": 0,
            "successful_queries": 0,
            "blocked_queries": 0,
            "insufficient_context_queries": 0,
            "average_latency_ms": 0.0,
            "average_retrieval_latency_ms": 0.0,
            "average_rerank_latency_ms": 0.0,
            "average_generation_latency_ms": 0.0,
            "average_grounding_score": 0.0,
            "grounded_response_pct": 0.0,
            "average_compression_ratio": 1.0,
            "total_tokens_saved": 0,
            "average_retrieved_chunks": 0.0,
            "average_selected_chunks": 0.0,
        }


def get_recent(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the most recent query records (latest first), bounded by limit."""
    safe_limit = min(max(int(limit), 1), 200)
    try:
        conn = _get_connection(db_path)
        rows = conn.execute(
            """
            SELECT
                timestamp, doc_id, answer_status, success,
                grounding_score, total_latency_ms, tokens_saved,
                retrieved_chunks, selected_chunks_count,
                compression_ratio, input_guard_status, output_guard_status
            FROM query_analytics
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("Analytics get_recent failed: %s", exc)
        return []
