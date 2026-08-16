from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.guardrail.pipeline import guarded_query_pipeline
from backend.documents.manager import get_document_manager
from backend.documents.models import DocumentMetadata, DocumentUploadResponse, DocumentListResponse
from backend.observability.health import get_system_health
from backend.observability.metrics import record_query, get_summary, get_recent

app = FastAPI(
    title="CacheLingua API",
    description="Compressed Document Retrieval & Context-Calibrated RAG API with Guardrails & Grounding Verification",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)


class QueryRequest(BaseModel):
    doc_id: str = Field(..., description="ID of target document")
    question: str = Field(..., description="User query question")
    k: Optional[int] = Field(10, description="Top-K vector candidates to retrieve")
    top_n: Optional[int] = Field(5, description="Top-N candidates to rerank")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/query")
def query_endpoint(request: QueryRequest):
    """
    Executes full guarded CacheLingua pipeline:
    Input Guardrail -> Phase 2 Retrieval -> Phase 3 Reranking -> Phase 4 Budget ->
    Sufficiency Check -> Groq Generation -> Output Guard & Grounding Validation.
    """
    try:
        result = guarded_query_pipeline(
            doc_id=request.doc_id,
            question=request.question,
            k=request.k or 10,
            top_n=request.top_n or 5,
        )
        # Phase 8: record analytics — fire-and-forget, never blocks response
        try:
            record_query(result)
        except Exception:
            pass
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── OBSERVABILITY ENDPOINTS (Phase 8) ──────────────────── #

@app.get("/system/health")
def system_health_endpoint():
    """Returns structured system health: Redis, ChromaDB, LLM status, document count."""
    return get_system_health()


@app.get("/analytics/summary")
def analytics_summary_endpoint():
    """Returns aggregated query analytics: totals, averages, latency, grounding."""
    return get_summary()


@app.get("/analytics/recent")
def analytics_recent_endpoint(limit: int = 50):
    """Returns the most recent query analytics records (metadata only, no question text)."""
    return {"queries": get_recent(limit=limit)}


# ─── DOCUMENT MANAGEMENT ENDPOINTS ───────────────────────── #

@app.get("/documents", response_model=DocumentListResponse)
def list_documents_endpoint():
    """Returns list of all active ingested documents with metadata."""
    manager = get_document_manager()
    docs = manager.list_documents()
    return {"documents": docs}


@app.get("/documents/{doc_id}", response_model=DocumentMetadata)
def get_document_endpoint(doc_id: str):
    """Retrieves structured metadata for a specific document."""
    manager = get_document_manager()
    doc = manager.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return doc


@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document_endpoint(
    file: UploadFile = File(...),
    doc_id: Optional[str] = Form(None)
):
    """
    Uploads a text document and processes it through the full ingestion pipeline:
    File -> Text Extraction -> Phase 1 Compression & Cache -> Phase 2 Embedding & Vector Indexing.
    Increments doc_version automatically on re-upload.
    """
    manager = get_document_manager()
    try:
        file_bytes = await file.read()
        target_doc_id = doc_id.strip() if doc_id and doc_id.strip() else file.filename
        
        result = manager.process_and_store_document(
            filename=file.filename or target_doc_id,
            file_bytes=file_bytes,
            custom_doc_id=target_doc_id
        )

        return DocumentUploadResponse(
            success=True,
            message=f"Document '{target_doc_id}' uploaded and indexed successfully (version {result['document'].doc_version}).",
            document=result["document"],
            ingestion_summary=result["ingestion_summary"]
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion error: {str(e)}")


@app.delete("/documents/{doc_id}")
def delete_document_endpoint(doc_id: str):
    """Deletes a document from registry and vector store index."""
    manager = get_document_manager()
    deleted = manager.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found or already deleted.")
    return {
        "success": True,
        "message": f"Document '{doc_id}' deleted successfully."
    }
