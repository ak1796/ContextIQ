# CacheLingua Developer Dashboard Frontend

Modern AI Infrastructure & Context-Calibrated RAG Developer Dashboard built with **Next.js 15 (App Router)**, **TypeScript**, and **Tailwind CSS**.

## Features

- **Query Bench**: Interactive console to query ingested document contexts, test parameters (`k`, `top_n`), and inspect prompt injection defenses.
- **Pipeline Observability Bar**: Multi-color stacked latency breakdown covering Phase 1 Ingestion through Phase 5 Output Guardrails.
- **Token Compression Analytics**: Live tracking of `original_tokens`, `compressed_tokens`, `tokens_saved`, and `compression_ratio`.
- **Phase 5 Guardrails & Grounding Audit**: Real-time display of input security status, risk levels, and sentence-level MiniLM cosine grounding scores.
- **Context Inspector**: Tabbed viewer to inspect Selected Chunks (Phase 4), Reranked Chunks (Phase 3), and Retrieved Chunks (Phase 2) side-by-side with original vs. compressed text.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React (`lucide-react`)

## Getting Started

1. Ensure the CacheLingua FastAPI backend is running on `http://localhost:8000`:
   ```bash
   python -m uvicorn api.main:app --reload
   ```

2. Run the Next.js development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.
