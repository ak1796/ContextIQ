import os
import json
import re
import logging
from threading import Lock
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from backend.documents.models import DocumentMetadata
from backend.ingest.ingest import ingest_document
from backend.ingest.cache import get_cache, CacheBackend
from backend.retrieval.vector_store import index_chunks, get_chroma_client, sanitize_collection_name

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit
REGISTRY_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "documents_registry.json")


class DocumentManager:
    """
    Manages document metadata, text extraction, Phase 1 compression,
    Phase 2 vector indexing, versioning, and document deletion.
    """

    def __init__(self, registry_file: str = REGISTRY_FILE_PATH, cache: Optional[CacheBackend] = None):
        self.registry_file = registry_file
        self.cache = cache or get_cache()
        self._lock = Lock()
        self._registry: Dict[str, DocumentMetadata] = {}
        self._load_registry()
        # NOTE: _ensure_sample_docs() is intentionally NOT called here.
        # Calling process_and_store_document() at startup would run LLMLingua-2
        # model inference synchronously, blocking FastAPI from accepting any
        # requests until the model loads and completes compression (30–120s).
        # Sample documents can be uploaded via POST /documents/upload or
        # the Document Ingest UI tab.

    def _load_registry(self):
        """Loads persistent document metadata registry from JSON file."""
        with self._lock:
            if os.path.exists(self.registry_file):
                try:
                    with open(self.registry_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for doc_id, meta_dict in data.items():
                            self._registry[doc_id] = DocumentMetadata(**meta_dict)
                except Exception as err:
                    logger.warning(f"Error reading documents registry file '{self.registry_file}': {err}")

    def _save_registry(self):
        """Saves persistent document metadata registry to JSON file."""
        with self._lock:
            try:
                data = {doc_id: meta.model_dump() for doc_id, meta in self._registry.items()}
                with open(self.registry_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as err:
                logger.error(f"Error saving documents registry file '{self.registry_file}': {err}")

    def _ensure_sample_docs(self):
        """Auto-registers doc1.txt if sample_docs/doc1.txt exists and is not yet in registry."""
        sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_docs", "doc1.txt")
        if os.path.exists(sample_path) and "doc1.txt" not in self._registry:
            try:
                with open(sample_path, "r", encoding="utf-8") as f:
                    text = f.read()
                size = os.path.getsize(sample_path)
                self.process_and_store_document(
                    filename="doc1.txt",
                    file_bytes=text.encode("utf-8"),
                    custom_doc_id="doc1.txt"
                )
            except Exception as err:
                logger.warning(f"Failed to auto-index sample document doc1.txt: {err}")

    def list_documents(self) -> List[DocumentMetadata]:
        """Returns list of all active (non-deleted) document metadata objects."""
        with self._lock:
            return [meta for meta in self._registry.values() if meta.status != "deleted"]

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Returns document metadata for doc_id if exists and not deleted."""
        with self._lock:
            meta = self._registry.get(doc_id)
            if meta and meta.status != "deleted":
                return meta
            return None

    def validate_file(self, filename: str, file_bytes: bytes):
        """
        Validates uploaded file:
        - Rejects empty files
        - Enforces MAX_FILE_SIZE_BYTES
        - Checks allowed extension
        - Validates plain-text content
        """
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ValueError(f"File size exceeds maximum allowed limit of {max_mb}MB.")

        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise ValueError(f"Unsupported file format '{ext}'. Allowed formats: {allowed_str}")

        # Check for binary null bytes
        if b"\x00" in file_bytes[:1024]:
            raise ValueError("Uploaded file appears to be binary or corrupted text.")

    def extract_text(self, file_bytes: bytes) -> str:
        """Extracts text string safely from file bytes."""
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return file_bytes.decode("latin-1")
            except UnicodeDecodeError:
                raise ValueError("Could not decode file content as text.")

    def process_and_store_document(
        self,
        filename: str,
        file_bytes: bytes,
        custom_doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes uploaded document through full CacheLingua pipeline:
        1. Validates file and extracts text.
        2. Determines doc_id (sanitized filename or custom_doc_id).
        3. Executes Phase 1 ingestion (compress + cache). Automatically increments doc_version on re-upload.
        4. Executes Phase 2 vector store indexing (embeddings + ChromaDB).
        5. Updates and persists DocumentMetadata registry.
        """
        self.validate_file(filename, file_bytes)
        text = self.extract_text(file_bytes)

        if not text.strip():
            raise ValueError("Extracted text is empty or contains only whitespace.")

        doc_id = custom_doc_id or filename.strip()
        # Clean doc_id whitespace
        doc_id = doc_id.strip()

        # Step 1: Phase 1 Ingestion (compression + cache entry + doc_version increment)
        ingest_res = ingest_document(text=text, doc_id=doc_id, cache=self.cache)
        doc_version = ingest_res["doc_version"]
        records = ingest_res.get("records", [])

        # Step 2: Phase 2 Vector Indexing
        chunk_count = index_chunks(doc_id=doc_id, doc_version=doc_version, chunks=records)

        now_iso = datetime.now(timezone.utc).isoformat()
        
        with self._lock:
            existing = self._registry.get(doc_id)
            created_at = existing.created_at if existing else now_iso

            meta = DocumentMetadata(
                doc_id=doc_id,
                doc_version=doc_version,
                filename=filename,
                size=len(file_bytes),
                status="indexed",
                chunk_count=chunk_count,
                created_at=created_at,
                updated_at=now_iso,
            )
            self._registry[doc_id] = meta

        self._save_registry()

        return {
            "document": meta,
            "ingestion_summary": {
                "doc_id": doc_id,
                "doc_version": doc_version,
                "total_chunks": chunk_count,
                "evicted_count": ingest_res.get("evicted_count", 0),
            }
        }

    def delete_document(self, doc_id: str) -> bool:
        """
        Deletes document from registry and vector store collection.
        Returns True if document was deleted, False if not found.
        """
        with self._lock:
            meta = self._registry.get(doc_id)
            if not meta or meta.status == "deleted":
                return False
            meta.status = "deleted"
            meta.updated_at = datetime.now(timezone.utc).isoformat()

        # Delete ChromaDB collection if present
        try:
            client = get_chroma_client()
            coll_name = sanitize_collection_name(doc_id)
            existing_colls = [c.name for c in client.list_collections()]
            if coll_name in existing_colls:
                client.delete_collection(coll_name)
        except Exception as err:
            logger.warning(f"Error deleting Chroma collection for doc_id '{doc_id}': {err}")

        self._save_registry()
        return True


_DOCUMENT_MANAGER_INSTANCE = None


def get_document_manager() -> DocumentManager:
    """Singleton getter for DocumentManager."""
    global _DOCUMENT_MANAGER_INSTANCE
    if _DOCUMENT_MANAGER_INSTANCE is None:
        _DOCUMENT_MANAGER_INSTANCE = DocumentManager()
    return _DOCUMENT_MANAGER_INSTANCE
