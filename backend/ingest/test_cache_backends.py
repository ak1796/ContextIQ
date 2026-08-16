import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingest.cache import (
    SQLiteCacheBackend,
    compute_cache_key,
    DEFAULT_MAX_CACHE_SIZE,
)


def test_sqlite_backend():
    print("--- Testing SQLite Cache Backend ---")
    db_file = "test_sqlite_cache.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    cache = SQLiteCacheBackend(db_path=db_file)

    # 1. Key computation & set/get
    key = compute_cache_key("doc1", "Hello world", 0)
    assert len(key) == 16, f"Key length must be 16, got {len(key)}"

    data = {
        "doc_id": "doc1",
        "compressed_text": "Hello",
        "original_text": "Hello world",
        "doc_version": 1,
        "chunk_index": 0,
        "embedding": None,
        "created_at": "2026-08-15T20:00:00Z",
    }
    cache.set(key, data)
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved["compressed_text"] == "Hello"
    assert retrieved["original_text"] == "Hello world"
    assert retrieved["doc_version"] == 1
    assert retrieved["embedding"] is None

    # 2. Versioning
    v1 = cache.get_doc_version("doc1")
    assert v1 == 1
    v2 = cache.increment_doc_version("doc1")
    assert v2 == 2
    v3 = cache.get_doc_version("doc1")
    assert v3 == 2

    # 3. LRU eviction
    cache.clear()
    small_max = 3
    for i in range(5):
        k_i = compute_cache_key("doc1", f"text {i}", i)
        cache.set(
            k_i,
            {
                "doc_id": "doc1",
                "compressed_text": f"txt {i}",
                "original_text": f"text {i}",
                "doc_version": 1,
                "chunk_index": i,
                "embedding": None,
                "created_at": "2026-08-15T20:00:00Z",
            },
        )
        time.sleep(0.01)

    evicted = cache.evict_lru(max_size=small_max)
    assert evicted == 2, f"Expected 2 evicted entries, got {evicted}"
    assert cache.size() == small_max, f"Cache size should be {small_max}, got {cache.size()}"

    # Cleanup
    try:
        if os.path.exists(db_file):
            os.remove(db_file)
    except Exception:
        pass

    print("[SUCCESS] SQLite Cache Backend Tests Passed!")



if __name__ == "__main__":
    test_sqlite_backend()
