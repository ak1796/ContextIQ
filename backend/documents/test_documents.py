import os
import uuid
import pytest
from backend.documents.manager import DocumentManager
from backend.documents.models import DocumentMetadata
from backend.ingest.cache import get_cache
from backend.retrieval.retriever import retrieve_top_k


@pytest.fixture
def doc_manager(tmp_path):
    """Fixture returning a fresh DocumentManager with temporary registry path."""
    registry_file = str(tmp_path / "test_documents_registry.json")
    cache = get_cache()
    manager = DocumentManager(registry_file=registry_file, cache=cache)
    return manager


def test_process_and_store_text_document(doc_manager):
    # Use unique filename per run to avoid stale doc_version in shared cache
    filename = f"test_upload_doc_{uuid.uuid4().hex[:8]}.txt"
    content = "ContextIQ accelerates retrieval-augmented generation by compressing prompt text at the sentence level."
    file_bytes = content.encode("utf-8")

    result = doc_manager.process_and_store_document(filename=filename, file_bytes=file_bytes)
    assert result["document"] is not None
    meta = result["document"]

    assert meta.doc_id == filename
    assert meta.doc_version == 1
    assert meta.status == "indexed"
    assert meta.chunk_count > 0
    assert meta.size == len(file_bytes)


def test_reupload_increments_version(doc_manager):
    # Use unique filename per run to avoid stale doc_version in shared cache
    filename = f"version_test_{uuid.uuid4().hex[:8]}.txt"
    content_v1 = "Initial version text content for ContextIQ system document."
    content_v2 = "Updated second version content for ContextIQ system document with new details."

    res1 = doc_manager.process_and_store_document(filename=filename, file_bytes=content_v1.encode("utf-8"))
    meta1 = res1["document"]
    assert meta1.doc_version == 1

    res2 = doc_manager.process_and_store_document(filename=filename, file_bytes=content_v2.encode("utf-8"))
    meta2 = res2["document"]
    assert meta2.doc_version == 2


def test_invalid_file_type_rejected(doc_manager):
    filename = "script.exe"
    content = b"\x7fELF\x01\x01\x01\x00"

    with pytest.raises(ValueError, match="Unsupported file format"):
        doc_manager.process_and_store_document(filename=filename, file_bytes=content)


def test_empty_document_rejected(doc_manager):
    filename = "empty.txt"
    content = b""

    with pytest.raises(ValueError, match="empty"):
        doc_manager.process_and_store_document(filename=filename, file_bytes=content)


def test_oversized_file_rejected(doc_manager):
    filename = "huge.txt"
    content = b"A" * (6 * 1024 * 1024)  # 6 MB

    with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
        doc_manager.process_and_store_document(filename=filename, file_bytes=content)


def test_list_and_get_documents(doc_manager):
    doc_manager.process_and_store_document(filename="list_doc1.txt", file_bytes=b"Content for list doc 1.")
    doc_manager.process_and_store_document(filename="list_doc2.txt", file_bytes=b"Content for list doc 2.")

    docs = doc_manager.list_documents()
    doc_ids = [d.doc_id for d in docs]
    assert "list_doc1.txt" in doc_ids
    assert "list_doc2.txt" in doc_ids

    fetched = doc_manager.get_document("list_doc1.txt")
    assert fetched is not None
    assert fetched.filename == "list_doc1.txt"


def test_delete_document(doc_manager):
    filename = "delete_target.txt"
    doc_manager.process_and_store_document(filename=filename, file_bytes=b"Target to be deleted.")

    assert doc_manager.get_document(filename) is not None

    deleted = doc_manager.delete_document(filename)
    assert deleted is True

    # Should not appear in active document list
    assert doc_manager.get_document(filename) is None


def test_retrieval_after_upload(doc_manager):
    filename = "retrieval_test.txt"
    text = "ContextIQ reduces LLM context cost by 60 percent using sentence level token pruning."
    doc_manager.process_and_store_document(filename=filename, file_bytes=text.encode("utf-8"))

    ret_out = retrieve_top_k(doc_id=filename, question="How much cost does ContextIQ reduce?", k=5)
    assert len(ret_out["results"]) > 0
    assert ret_out["doc_id"] == filename
