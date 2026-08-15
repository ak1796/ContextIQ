import re
import os
import chromadb
from typing import List, Dict, Any, Optional
from retrieval.embeddings import embed_texts

_CHROMA_CLIENT = None
CHROMA_PERSIST_DIR = "./chroma_db"


def get_chroma_client() -> chromadb.PersistentClient:
    """Return persistent ChromaDB client singleton."""
    global _CHROMA_CLIENT
    if _CHROMA_CLIENT is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _CHROMA_CLIENT = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _CHROMA_CLIENT


def sanitize_collection_name(doc_id: str) -> str:
    """
    Sanitize doc_id to meet ChromaDB collection name rules:
    - 3-63 characters
    - Only alphanumeric, underscores, or hyphens
    - Starts and ends with an alphanumeric character
    """
    # Replace non-alphanumeric/hyphen/underscore with underscore
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_id)
    # Ensure starts/ends with alphanumeric
    clean_name = clean_name.strip("_-")
    if len(clean_name) < 3:
        clean_name = f"doc_{clean_name}"
    if len(clean_name) > 63:
        clean_name = clean_name[:63].rstrip("_-")
    return clean_name


def get_collection(doc_id: str):
    """Retrieve or create ChromaDB collection for doc_id."""
    client = get_chroma_client()
    coll_name = sanitize_collection_name(doc_id)
    return client.get_or_create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})


def index_chunks(doc_id: str, doc_version: int, chunks: List[Dict[str, Any]]) -> int:
    """
    Indexes compressed chunks into ChromaDB:
    - Generates embeddings using sentence-transformers (all-MiniLM-L6-v2)
    - Stores compressed text, vector, and metadata (doc_id, doc_version, chunk_index, cache_key)
    Returns number of indexed chunks.
    """
    if not chunks:
        return 0

    collection = get_collection(doc_id)

    texts_to_embed = []
    ids = []
    metadatas = []
    documents = []

    for chunk in chunks:
        # Extract chunk details (supports both raw chunk dicts and ingestion record dicts)
        if "entry" in chunk:
            entry = chunk["entry"]
            chunk_idx = entry["chunk_index"]
            compressed_txt = entry["compressed_text"]
            cache_key = chunk["cache_key"]
        else:
            chunk_idx = chunk["chunk_index"]
            compressed_txt = chunk["compressed_text"]
            cache_key = chunk.get("cache_key", f"{doc_id}_{chunk_idx}")

        item_id = f"{doc_id}_v{doc_version}_c{chunk_idx}_{cache_key}"
        
        texts_to_embed.append(compressed_txt)
        documents.append(compressed_txt)
        ids.append(item_id)
        metadatas.append({
            "doc_id": str(doc_id),
            "doc_version": int(doc_version),
            "chunk_index": int(chunk_idx),
            "cache_key": str(cache_key),
        })

    embeddings = embed_texts(texts_to_embed)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(ids)
