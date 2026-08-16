from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Structured document metadata model."""
    doc_id: str = Field(..., description="Unique document identifier")
    doc_version: int = Field(1, description="Current document version (increments on re-upload)")
    filename: str = Field(..., description="Original uploaded filename")
    size: int = Field(..., description="File size in bytes")
    status: str = Field("indexed", description="Document status: indexed, processing, failed, deleted")
    chunk_count: int = Field(0, description="Total compressed chunks indexed in vector store")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: Optional[str] = Field(None, description="ISO 8601 last update timestamp")


class DocumentUploadResponse(BaseModel):
    """Response returned after uploading and indexing a document."""
    success: bool = Field(..., description="Whether ingestion and indexing succeeded")
    message: str = Field(..., description="Human-readable result message")
    document: Optional[DocumentMetadata] = Field(None, description="Metadata of the ingested document")
    ingestion_summary: Optional[Dict[str, Any]] = Field(None, description="Compression and chunking statistics")


class DocumentListResponse(BaseModel):
    """Response model for GET /documents."""
    documents: List[DocumentMetadata] = Field(default_factory=list, description="List of active documents")
