# ContextIQ Benchmark Results: Path A (Raw RAG) vs Path B (CacheLingua / ContextIQ)

> Generated: 2026-08-16 16:39:25  |  Questions: 45

Comparing **Uncompressed Raw RAG (Path A)** against the full **CacheLingua / ContextIQ pipeline (Path B)** across 45 benchmark questions (TXT, Markdown, CSV document types).

| Metric | Path A Raw RAG | Path B ContextIQ | Delta |
| :--- | :---: | :---: | :---: |
| **Questions evaluated** | 45 | 45 | --- |
| **Retrieval Recall@K** | 90.74% | 90.74% | +0.00% |
| **Retrieval Precision@K** | 45.41% | 45.41% | +0.00% |
| **Answer Correctness** | 87.69% | 78.88% | -8.81% |
| **Grounding Score** | 92.96% | 90.15% | -2.81% |
| **Hallucination Rate** | 8.89% | 17.78% | +8.89% |
| **Avg Tokens to LLM (raw / uncompressed)** | 114.0 tokens | --- | --- |
| **Avg Tokens to LLM (after compression)** | --- | 93.2 tokens | **18.21% reduction** |
| **Avg Tokens Saved per Query** | 0 | 20.8 | +20.80 tok |
| **Avg Compression Ratio** | 1.00x | 0.8289x | -0.17x |
| **CSV Exact-Match Accuracy** | 40.0% | 40.0% | +0.00% |
| **Average Total Latency** | 4458.88 ms | 2783.15 ms | -1675.73 ms |
| **Cache Hit Rate** | 97.78% | 100.0% | +2.22% |

## Key Takeaways

1. **Token Cost Savings**: CacheLingua (Path B) sent **93.2 tokens** to the LLM vs **114.0 tokens** for raw RAG -- a **18.21% reduction** in inference cost per query.
2. **Answer Quality**: Path B achieved **78.88% answer correctness** and **90.15% grounding score** on the 45-question benchmark.
3. **Structured CSV Retrieval**: CSV exact-match accuracy was **40.0%** using the hybrid structured-lookup routing path.
4. **Hallucination Control**: Hallucination rate was **17.78%** for Path B vs **8.89%** for raw RAG.
5. **Latency**: Path B averaged **2783.15 ms** end-to-end vs **4458.88 ms** for raw RAG.