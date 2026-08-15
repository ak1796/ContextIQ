'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { DocumentMetadata } from '@/lib/types';
import { fetchDocuments, uploadDocument, deleteDocument } from '@/lib/api';
import {
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Layers,
  HardDrive,
  Clock,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';

interface DocumentManagerViewProps {
  onSelectDocumentForQuery?: (docId: string) => void;
}

const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.json', '.csv', '.log'];

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function DocumentManagerView({ onSelectDocumentForQuery }: DocumentManagerViewProps) {
  const [documents, setDocuments]       = useState<DocumentMetadata[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState<boolean>(true);
  const [isUploading, setIsUploading]   = useState<boolean>(false);
  const [deletingId, setDeletingId]     = useState<string | null>(null);
  
  const [isDragging, setIsDragging]     = useState<boolean>(false);
  const [customDocId, setCustomDocId]   = useState<string>('');
  
  const [message, setMessage]           = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const fileInputRef                    = useRef<HTMLInputElement>(null);

  const loadDocs = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const list = await fetchDocuments();
      setDocuments(list);
    } catch {
      // Ignore
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    fetchDocuments().then((list) => {
      if (isMounted) {
        setDocuments(list);
        setIsLoadingDocs(false);
      }
    }).catch(() => {
      if (isMounted) setIsLoadingDocs(false);
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    // Client-side extension validation
    const ext = `.${file.name.split('.').pop()?.toLowerCase()}`;
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      setMessage({
        type: 'error',
        text: `Unsupported file extension '${ext}'. Supported formats: ${SUPPORTED_EXTENSIONS.join(', ')}`,
      });
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setMessage({
        type: 'error',
        text: 'File size exceeds maximum limit of 5MB.',
      });
      return;
    }

    setIsUploading(true);
    setMessage(null);

    try {
      const res = await uploadDocument(file, customDocId.trim() || undefined);
      setMessage({
        type: 'success',
        text: res.message || `Document '${file.name}' indexed successfully.`,
      });
      setCustomDocId('');
      await loadDocs();
    } catch (err: unknown) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to upload document.',
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDelete = async (docId: string) => {
    if (!confirm(`Are you sure you want to delete document '${docId}' from the vector store?`)) {
      return;
    }

    setDeletingId(docId);
    setMessage(null);
    try {
      await deleteDocument(docId);
      setMessage({
        type: 'success',
        text: `Document '${docId}' deleted successfully.`,
      });
      await loadDocs();
    } catch (err: unknown) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to delete document.',
      });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header section */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-brand font-semibold text-[color:var(--foreground)]">
            Document Ingestion &amp; Version Management
          </h2>
          <p className="text-xs font-sans-plex text-[color:var(--muted)]">
            Upload text documents to compress (Phase 1 LLMLingua-2), embed (Phase 2 MiniLM), and index into ChromaDB.
          </p>
        </div>

        <button
          onClick={loadDocs}
          disabled={isLoadingDocs}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-sans-plex font-medium rounded-lg border transition-colors disabled:opacity-50"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderColor: 'var(--border)',
            color: 'var(--foreground)',
          }}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoadingDocs ? 'animate-spin' : ''}`} />
          <span>Refresh Registry</span>
        </button>
      </div>

      {/* Upload Drag & Drop Dropzone */}
      <Card glow className="space-y-4">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className="p-8 border-2 border-dashed rounded-xl text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3"
          style={{
            backgroundColor: isDragging ? 'color-mix(in srgb, var(--primary) 8%, transparent)' : 'var(--surface-muted)',
            borderColor: isDragging ? 'var(--primary)' : 'var(--border)',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
            accept={SUPPORTED_EXTENSIONS.join(',')}
            className="hidden"
          />

          <div
            className="p-3 rounded-full"
            style={{
              backgroundColor: 'color-mix(in srgb, var(--primary) 12%, transparent)',
              border: '1px solid color-mix(in srgb, var(--primary) 25%, transparent)',
            }}
          >
            {isUploading ? (
              <Loader2 className="h-6 w-6 animate-spin text-[color:var(--primary)]" />
            ) : (
              <UploadCloud className="h-6 w-6 text-[color:var(--primary)]" />
            )}
          </div>

          <div>
            <p className="text-sm font-sans-plex font-semibold text-[color:var(--foreground)]">
              {isUploading ? 'Compressing & Indexing Document…' : 'Click or Drag & Drop Document Here'}
            </p>
            <p className="text-xs font-mono-plex text-[color:var(--muted)] mt-1">
              Supported text formats: {SUPPORTED_EXTENSIONS.join(' ')} (Max 5MB)
            </p>
          </div>
        </div>

        {/* Optional Custom Target Doc ID Input */}
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <label htmlFor="custom-doc-id" className="text-xs font-sans-plex text-[color:var(--muted)]">
            Custom Document ID (optional):
          </label>
          <input
            id="custom-doc-id"
            type="text"
            value={customDocId}
            disabled={isUploading}
            onChange={(e) => setCustomDocId(e.target.value)}
            placeholder="e.g. doc1.txt (leave blank to use filename)"
            className="px-3 py-1.5 text-xs font-mono-plex rounded-lg border outline-none max-w-sm flex-1"
            style={{
              backgroundColor: 'var(--surface-muted)',
              borderColor: 'var(--border)',
              color: 'var(--foreground)',
            }}
          />
        </div>
      </Card>

      {/* Notification Banner */}
      {message && (
        <div
          role="alert"
          className="p-4 rounded-xl flex items-center gap-3 text-xs font-sans-plex animate-fade-in"
          style={{
            backgroundColor: message.type === 'success'
              ? 'color-mix(in srgb, var(--success) 10%, transparent)'
              : 'color-mix(in srgb, var(--danger) 10%, transparent)',
            border: `1px solid ${
              message.type === 'success'
                ? 'color-mix(in srgb, var(--success) 30%, transparent)'
                : 'color-mix(in srgb, var(--danger) 30%, transparent)'
            }`,
            color: message.type === 'success' ? 'var(--success)' : 'var(--danger)',
          }}
        >
          {message.type === 'success' ? (
            <CheckCircle2 className="h-5 w-5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Document List Section */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[color:var(--border-subtle)]">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-[color:var(--primary)]" />
            <h3 className="text-sm font-brand font-semibold text-[color:var(--foreground)]">
              Active Vector Store Documents ({documents.length})
            </h3>
          </div>
        </div>

        {isLoadingDocs ? (
          <div className="p-8 text-center text-xs font-mono-plex text-[color:var(--muted)] flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-[color:var(--primary)]" />
            <span>Loading document registry…</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center text-xs font-mono-plex text-[color:var(--muted)] border border-dashed rounded-lg">
            No active documents found. Upload a .txt file above to start querying!
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.doc_id}
                className="p-4 rounded-xl border flex flex-wrap items-center justify-between gap-4 transition-all"
                style={{
                  backgroundColor: 'var(--surface-elevated)',
                  borderColor: 'var(--border-subtle)',
                }}
              >
                {/* Meta details */}
                <div className="space-y-1 min-w-[220px]">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-[color:var(--primary)] shrink-0" />
                    <span className="text-sm font-mono-plex font-bold text-[color:var(--foreground)]">
                      {doc.doc_id}
                    </span>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-mono-plex font-semibold"
                      style={{
                        backgroundColor: 'color-mix(in srgb, var(--phase-budget) 15%, transparent)',
                        color: 'var(--phase-budget)',
                        border: '1px solid color-mix(in srgb, var(--phase-budget) 30%, transparent)',
                      }}
                    >
                      v{doc.doc_version}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono-plex text-[color:var(--muted)]">
                    <span className="flex items-center gap-1">
                      <HardDrive className="h-3 w-3" />
                      {formatBytes(doc.size)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Layers className="h-3 w-3" />
                      {doc.chunk_count} {doc.chunk_count === 1 ? 'chunk' : 'chunks'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(doc.created_at)}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {onSelectDocumentForQuery && (
                    <button
                      onClick={() => onSelectDocumentForQuery(doc.doc_id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-sans-plex font-semibold rounded-lg transition-all"
                      style={{
                        backgroundColor: 'var(--primary)',
                        color: 'var(--primary-foreground)',
                      }}
                    >
                      <span>Query Document</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(doc.doc_id)}
                    disabled={deletingId === doc.doc_id}
                    className="p-1.5 rounded-lg border text-[color:var(--danger)] transition-all hover:bg-[color:var(--danger)]/10 disabled:opacity-50"
                    style={{ borderColor: 'color-mix(in srgb, var(--danger) 30%, transparent)' }}
                    title={`Delete document '${doc.doc_id}'`}
                  >
                    {deletingId === doc.doc_id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
