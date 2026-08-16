import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL_INSTANCE = None
MODEL_NAME = "all-MiniLM-L6-v2"


def get_embedding_model() -> SentenceTransformer:
    """
    Returns a singleton instance of the SentenceTransformer embedding model.
    Loaded once and reused across invocations on CPU.
    """
    global _EMBEDDING_MODEL_INSTANCE
    if _EMBEDDING_MODEL_INSTANCE is None:
        logger.info(f"Loading embedding model '{MODEL_NAME}' on CPU...")
        _EMBEDDING_MODEL_INSTANCE = SentenceTransformer(MODEL_NAME, device="cpu")
        print(f"[STARTUP] Loaded {MODEL_NAME}")
    return _EMBEDDING_MODEL_INSTANCE


def embed_text(text: str) -> List[float]:
    """Generates a 384-dimensional vector embedding for a single text string."""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Batch generates vector embeddings for a list of text strings."""
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [emb.tolist() for emb in embeddings]
