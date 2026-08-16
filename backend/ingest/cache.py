import os
import json
import time
import hashlib
import sqlite3
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

DEFAULT_MAX_CACHE_SIZE = 5000
DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days in seconds


def compute_cache_key(doc_id: str, chunk_text: str, chunk_index: int) -> str:
    """
    Cache key format: hash(doc_id + chunk_text + chunk_index)
    sha256 truncated to 16 hex characters.
    """
    raw = f"{doc_id}{chunk_text}{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class CacheBackend(ABC):
    """Abstract base class for ingest cache implementations."""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached entry by key. Returns None if not found or expired."""
        pass

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl: int = DEFAULT_TTL_SECONDS) -> None:
        """Store a cache entry with a specified TTL (in seconds)."""
        pass

    @abstractmethod
    def get_doc_version(self, doc_id: str) -> int:
        """Get current version for doc_id. Defaults to 1 if doc_id has not been seen."""
        pass

    @abstractmethod
    def increment_doc_version(self, doc_id: str) -> int:
        """Increment version for doc_id and return the new version integer."""
        pass

    @abstractmethod
    def register_or_increment_doc_version(self, doc_id: str) -> int:
        """Register doc_id (version 1) or increment version if already registered."""
        pass


    @abstractmethod
    def evict_lru(self, max_size: int = DEFAULT_MAX_CACHE_SIZE) -> int:
        """Evict oldest used entries if size exceeds max_size. Returns number of evicted keys."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return total active key count in cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from cache (mainly for testing)."""
        pass


class RedisCacheBackend(CacheBackend):
    """Redis-backed cache storage."""

    def __init__(self, redis_client=None, host="localhost", port=6379, db=0):
        if redis_client is not None:
            self.r = redis_client
        else:
            import redis
            self.r = redis.Redis(host=host, port=port, db=db, socket_timeout=2)
            self.r.ping()

        self.key_prefix = "ingest_cache:"
        self.lru_zset = "ingest_cache_lru"
        self.doc_versions_hash = "ingest_doc_versions"

    def _full_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        full_k = self._full_key(key)
        data = self.r.get(full_k)
        if not data:
            self.r.zrem(self.lru_zset, key)
            return None

        # Update last accessed timestamp in ZSET and refresh TTL
        now = time.time()
        self.r.zadd(self.lru_zset, {key: now})
        self.r.expire(full_k, DEFAULT_TTL_SECONDS)

        try:
            val = json.loads(data.decode("utf-8"))
            return val
        except Exception:
            return None

    def set(self, key: str, value: Dict[str, Any], ttl: int = DEFAULT_TTL_SECONDS) -> None:
        full_k = self._full_key(key)
        now = time.time()
        payload = json.dumps(value)

        self.r.setex(full_k, ttl, payload)
        self.r.zadd(self.lru_zset, {key: now})

    def get_doc_version(self, doc_id: str) -> int:
        ver = self.r.hget(self.doc_versions_hash, doc_id)
        if ver is None:
            return 1
        return int(ver.decode("utf-8"))

    def increment_doc_version(self, doc_id: str) -> int:
        new_ver = self.r.hincrby(self.doc_versions_hash, doc_id, 1)
        return int(new_ver)

    def register_or_increment_doc_version(self, doc_id: str) -> int:
        exists = self.r.hexists(self.doc_versions_hash, doc_id)
        if not exists:
            self.r.hset(self.doc_versions_hash, doc_id, 1)
            return 1
        else:
            new_ver = self.r.hincrby(self.doc_versions_hash, doc_id, 1)
            return int(new_ver)


    def size(self) -> int:
        return self.r.zcard(self.lru_zset)

    def evict_lru(self, max_size: int = DEFAULT_MAX_CACHE_SIZE) -> int:
        current_count = self.size()
        if current_count <= max_size:
            return 0

        to_remove_count = current_count - max_size
        oldest_keys = self.r.zrange(self.lru_zset, 0, to_remove_count - 1)
        if not oldest_keys:
            return 0

        evicted = 0
        for k_bytes in oldest_keys:
            k_str = k_bytes.decode("utf-8") if isinstance(k_bytes, bytes) else str(k_bytes)
            self.r.delete(self._full_key(k_str))
            self.r.zrem(self.lru_zset, k_str)
            evicted += 1

        return evicted

    def clear(self) -> None:
        keys = self.r.zrange(self.lru_zset, 0, -1)
        for k_bytes in keys:
            k_str = k_bytes.decode("utf-8") if isinstance(k_bytes, bytes) else str(k_bytes)
            self.r.delete(self._full_key(k_str))
        self.r.delete(self.lru_zset)
        self.r.delete(self.doc_versions_hash)


class SQLiteCacheBackend(CacheBackend):
    """SQLite-backed fallback cache storage."""

    def __init__(self, db_path: str = "ingest_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    doc_id TEXT,
                    compressed_text TEXT,
                    original_text TEXT,
                    doc_version INTEGER,
                    chunk_index INTEGER,
                    embedding TEXT,
                    created_at TEXT,
                    last_accessed_at REAL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS doc_versions (
                    doc_id TEXT PRIMARY KEY,
                    version INTEGER
                )
                """
            )
            conn.commit()

    def _cleanup_expired(self, conn, ttl: int = DEFAULT_TTL_SECONDS):
        cutoff = time.time() - ttl
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_entries WHERE last_accessed_at < ?", (cutoff,))

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        cutoff = now - DEFAULT_TTL_SECONDS
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT compressed_text, original_text, doc_version, chunk_index, embedding, created_at, last_accessed_at
                FROM cache_entries WHERE key = ?
                """,
                (key,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            last_accessed = row[6]
            if last_accessed < cutoff:
                cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                conn.commit()
                return None

            cursor.execute("UPDATE cache_entries SET last_accessed_at = ? WHERE key = ?", (now, key))
            conn.commit()

            compressed_text, original_text, doc_version, chunk_index, embedding, created_at, _ = row
            return {
                "compressed_text": compressed_text,
                "original_text": original_text,
                "doc_version": doc_version,
                "chunk_index": chunk_index,
                "embedding": json.loads(embedding) if embedding else None,
                "created_at": created_at,
            }

    def set(self, key: str, value: Dict[str, Any], ttl: int = DEFAULT_TTL_SECONDS) -> None:
        now = time.time()
        doc_id = value.get("doc_id", "")
        compressed_text = value.get("compressed_text", "")
        original_text = value.get("original_text", "")
        doc_version = value.get("doc_version", 1)
        chunk_index = value.get("chunk_index", 0)
        embedding_json = json.dumps(value.get("embedding")) if value.get("embedding") is not None else None
        created_at = value.get("created_at", datetime.now(timezone.utc).isoformat())

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache_entries
                (key, doc_id, compressed_text, original_text, doc_version, chunk_index, embedding, created_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (key, doc_id, compressed_text, original_text, doc_version, chunk_index, embedding_json, created_at, now),
            )
            conn.commit()

    def get_doc_version(self, doc_id: str) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM doc_versions WHERE doc_id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return 1

    def increment_doc_version(self, doc_id: str) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM doc_versions WHERE doc_id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                new_ver = row[0] + 1
                cursor.execute("UPDATE doc_versions SET version = ? WHERE doc_id = ?", (new_ver, doc_id))
            else:
                new_ver = 2
                cursor.execute("INSERT INTO doc_versions (doc_id, version) VALUES (?, ?)", (doc_id, new_ver))
            conn.commit()
            return new_ver

    def register_or_increment_doc_version(self, doc_id: str) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM doc_versions WHERE doc_id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                new_ver = row[0] + 1
                cursor.execute("UPDATE doc_versions SET version = ? WHERE doc_id = ?", (new_ver, doc_id))
            else:
                new_ver = 1
                cursor.execute("INSERT INTO doc_versions (doc_id, version) VALUES (?, ?)", (doc_id, new_ver))
            conn.commit()
            return new_ver


    def size(self) -> int:
        with self._get_conn() as conn:
            self._cleanup_expired(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            row = cursor.fetchone()
            return row[0] if row else 0

    def evict_lru(self, max_size: int = DEFAULT_MAX_CACHE_SIZE) -> int:
        with self._get_conn() as conn:
            self._cleanup_expired(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            current_count = cursor.fetchone()[0]

            if current_count <= max_size:
                return 0

            to_delete = current_count - max_size
            cursor.execute(
                """
                DELETE FROM cache_entries
                WHERE key IN (
                    SELECT key FROM cache_entries
                    ORDER BY last_accessed_at ASC
                    LIMIT ?
                )
                """,
                (to_delete,),
            )
            conn.commit()
            return cursor.rowcount

    def clear(self) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_entries")
            cursor.execute("DELETE FROM doc_versions")
            conn.commit()


# Instantiate default cache at import time via try/except on Redis connection
try:
    import redis
    _client = redis.Redis(host="localhost", port=6379, socket_timeout=2)
    _client.ping()
    default_cache = RedisCacheBackend(redis_client=_client)
    CACHE_TYPE = "redis"
except Exception:
    default_cache = SQLiteCacheBackend()
    CACHE_TYPE = "sqlite"


def get_cache() -> CacheBackend:
    """Return the active global cache backend."""
    return default_cache
