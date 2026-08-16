# ContextIQ Benchmark Results: Path A (Raw RAG) vs Path B (CacheLingua / ContextIQ)

> Generated: 2026-08-16 17:06:44  |  Questions: 45

Comparing **Uncompressed Raw RAG (Path A)** against the full **CacheLingua / ContextIQ pipeline (Path B)** across 45 benchmark questions (TXT, Markdown, CSV document types).

| Metric | Path A Raw RAG | Path B ContextIQ | Delta |
| :--- | :---: | :---: | :---: |
| **Questions evaluated** | 45 | 45 | --- |
| **Retrieval Recall@K** | 88.52% | 88.52% | +0.00% |
| **Retrieval Precision@K** | 52.3% | 52.3% | +0.00% |
| **Answer Correctness** | 85.79% | 76.03% | -9.76% |
| **Grounding Score** | 98.52% | 98.7% | +0.18% |
| **Hallucination Rate** | 2.22% | 2.22% | +0.00% |
| **Avg Tokens to LLM (raw / uncompressed)** | 94.8 tokens | --- | --- |
| **Avg Tokens to LLM (after compression)** | --- | 74.0 tokens | **21.9% reduction** |
| **Avg Tokens Saved per Query** | 0 | 20.8 | +20.80 tok |
| **Avg Compression Ratio** | 1.00x | 0.8289x | -0.17x |
| **CSV Exact-Match Accuracy** | 40.0% | 33.33% | -6.67% |
| **Average Total Latency** | 3276.44 ms | 4060.47 ms | +784.03 ms |
| **Cache Hit Rate** | 93.33% | 91.11% | -2.22% |

## Key Takeaways

1. **Token Cost Savings**: CacheLingua (Path B) sent **74.0 tokens** to the LLM vs **94.8 tokens** for raw RAG -- a **21.9% reduction** in inference cost per query.
2. **Answer Quality**: Path B achieved **76.03% answer correctness** and **98.7% grounding score** on the 45-question benchmark.
3. **Structured CSV Retrieval**: CSV exact-match accuracy was **33.33%** using the hybrid structured-lookup routing path.
4. **Hallucination Control**: Hallucination rate was **2.22%** for Path B vs **2.22%** for raw RAG.
5. **Latency**: Path B averaged **4060.47 ms** end-to-end vs **3276.44 ms** for raw RAG.