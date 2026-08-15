"""
System Health Prober — Phase 8.

Performs lightweight, non-blocking checks on all subsystems:
Redis, ChromaDB vector store, Groq LLM API key presence,
and document registry count.

All checks are wrapped in try/except — this module never raises.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _check_redis() -> str:
    """Ping Redis via the existing cache backend. Returns 'connected' or 'unavailable'."""
    try:
        from ingest.cache import get_cache
        cache = get_cache()
        # Use a harmless sentinel key — no document data involved
        cache.get("__health_ping__")
        return "connected"
    except Exception as exc:
        logger.debug("Redis health check failed: %s", exc)
        return "unavailable"


def _check_vector_store() -> str:
    """Heartbeat the existing ChromaDB persistent client. Returns 'healthy' or 'unavailable'."""
    try:
        import chromadb
        from chromadb.config import Settings
        chroma_path = os.path.join(os.getcwd(), "chroma_db")
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        client.heartbeat()
        return "healthy"
    except Exception as exc:
        logger.debug("ChromaDB health check failed: %s", exc)
        return "unavailable"


def _check_llm() -> str:
    """Verify GROQ_API_KEY is configured (no API call made). Returns 'available' or 'unconfigured'."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    return "available" if api_key else "unconfigured"


def _get_document_count() -> int:
    """Return count of registered documents. Returns 0 on error."""
    try:
        from documents.manager import get_document_manager
        manager = get_document_manager()
        docs = manager.list_documents()
        return len(docs)
    except Exception as exc:
        logger.debug("Document count check failed: %s", exc)
        return 0


def get_system_health() -> Dict[str, Any]:
    """
    Returns structured system health information.
    Safe, cheap, non-blocking — suitable for frequent polling.
    """
    redis_status = _check_redis()
    vector_store_status = _check_vector_store()
    llm_status = _check_llm()
    doc_count = _get_document_count()

    overall = (
        "healthy"
        if redis_status == "connected"
        and vector_store_status == "healthy"
        and llm_status == "available"
        else "degraded"
    )

    return {
        "status": overall,
        "backend": True,
        "redis": redis_status,
        "vector_store": vector_store_status,
        "llm": llm_status,
        "documents": doc_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
