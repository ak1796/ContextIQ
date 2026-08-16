from backend.retrieval.embeddings import get_embedding_model, embed_text, embed_texts
from backend.retrieval.vector_store import get_collection, index_chunks, sanitize_collection_name
from backend.retrieval.retriever import retrieve_top_k


def __getattr__(name: str):
    if name == "ingest_and_index_document":
        from backend.retrieval.pipeline import ingest_and_index_document
        return ingest_and_index_document
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "get_embedding_model",
    "embed_text",
    "embed_texts",
    "get_collection",
    "index_chunks",
    "sanitize_collection_name",
    "retrieve_top_k",
    "ingest_and_index_document",
]
