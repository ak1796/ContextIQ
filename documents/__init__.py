"""
Document Ingestion & Management Layer for CacheLingua.
Handles document uploads, text extraction, version management, Phase 1 compression, and Phase 2 indexing.
"""

from documents.models import DocumentMetadata, DocumentUploadResponse
from documents.manager import DocumentManager, get_document_manager

__all__ = [
    "DocumentMetadata",
    "DocumentUploadResponse",
    "DocumentManager",
    "get_document_manager",
]
