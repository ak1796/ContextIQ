import {
  QueryPayload,
  QueryResponse,
  HealthResponse,
  DocumentMetadata,
  DocumentUploadResponse,
  DocumentListResponse,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export async function queryPipeline(payload: QueryPayload): Promise<QueryResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        doc_id: payload.doc_id,
        question: payload.question,
        k: payload.k || 10,
        top_n: payload.top_n || 5,
      }),
    });
  } catch {
    throw new Error('Unable to connect to CacheLingua API service. Please check your network or server status.');
  }

  if (!response.ok) {
    let errorMessage = `API service error (${response.status})`;
    try {
      const errData = await response.json();
      if (errData && errData.detail && typeof errData.detail === 'string') {
        errorMessage = errData.detail;
      }
    } catch {
      // Ignore JSON parse errors
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      cache: 'no-store',
    });
    if (!response.ok) {
      return { status: 'offline' };
    }
    const data = await response.json();
    return { status: data.status || 'ok' };
  } catch {
    return { status: 'offline' };
  }
}

export async function fetchDocuments(): Promise<DocumentMetadata[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/documents`, {
      method: 'GET',
      cache: 'no-store',
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch documents (${response.status})`);
    }
    const data: DocumentListResponse = await response.json();
    return data.documents || [];
  } catch {
    return [];
  }
}

export async function uploadDocument(file: File, docId?: string): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (docId && docId.trim()) {
    formData.append('doc_id', docId.trim());
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
  } catch {
    throw new Error('Network error while uploading document.');
  }

  if (!response.ok) {
    let errorMessage = `Upload failed (${response.status})`;
    try {
      const errData = await response.json();
      if (errData && errData.detail && typeof errData.detail === 'string') {
        errorMessage = errData.detail;
      }
    } catch {
      // Ignore JSON error
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function deleteDocument(docId: string): Promise<{ success: boolean; message: string }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(docId)}`, {
      method: 'DELETE',
    });
  } catch {
    throw new Error('Network error while deleting document.');
  }

  if (!response.ok) {
    let errorMessage = `Delete failed (${response.status})`;
    try {
      const errData = await response.json();
      if (errData && errData.detail && typeof errData.detail === 'string') {
        errorMessage = errData.detail;
      }
    } catch {
      // Ignore JSON error
    }
    throw new Error(errorMessage);
  }

  return response.json();
}
