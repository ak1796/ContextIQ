"""
ContextIQ Automated Benchmarking and Evaluation Suite.

Runs the 45-question benchmark across BOTH pipeline paths and records real metrics:
  Path A (raw):         bypass_compression=True  -> full uncompressed context to LLM
  Path B (cachelingua): bypass_compression=False -> full ContextIQ pipeline

Per question, per path, logs:
  - retrieval recall@k   (ground_truth_chunk membership + fact recall fallback)
  - retrieval precision@k
  - answer_correctness   (difflib fuzzy match + fact-presence score, max of both)
  - grounding_score      (from pipeline output-guard grounding module)
  - flagged_hallucinated (grounding_score < 0.70 AND an answer was actually generated)
  - total_latency_ms     (wall-clock from pipeline entry to return)
  - original_tokens / compressed_tokens / tokens_saved / compression_ratio
  - cache_hit            (heuristic: retrieval_latency_ms < 300ms with non-zero tokens)
  - csv_exact_match      (for CSV questions: 1.0 if expected value in answer, else 0.0)

Outputs:
  evaluation/results.json       -- full per-question results + aggregate summary
  evaluation/results_summary.md -- pitch-deck-ready markdown comparison table

Usage:
    python -m evaluation.run_benchmark
    python -m evaluation.run_benchmark --dry-run
    python -m evaluation.run_benchmark --force-reingest
"""

from __future__ import annotations

import os
import sys
import time
import json
import argparse
import difflib
import logging
import traceback
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Workspace root so backend.* imports resolve
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

# ---------------------------------------------------------------------------
# Logging: suppress noisy third-party libraries
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
    stream=sys.stderr,
)
for _lib in ["sentence_transformers", "chromadb", "transformers", "httpx", "httpcore", "llmlingua"]:
    logging.getLogger(_lib).setLevel(logging.ERROR)
logger = logging.getLogger("benchmark")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EVAL_DIR          = os.path.join(WORKSPACE_ROOT, "evaluation")
BENCHMARK_QA_FILE = os.path.join(EVAL_DIR, "benchmark_qa.json")
RESULTS_JSON_FILE = os.path.join(EVAL_DIR, "results.json")
SUMMARY_MD_FILE   = os.path.join(EVAL_DIR, "results_summary.md")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
HALLUCINATION_THRESHOLD = 0.70   # grounding_score below this = potential hallucination

# ---------------------------------------------------------------------------
# Ground-truth benchmark document contents (self-contained for reproducibility)
# ---------------------------------------------------------------------------
TXT_DOC_CONTENT = (
    "LinguaCorp was founded in 2021 by Sarah Chen.\n"
    "The company headquarters is located in Austin, Texas.\n"
    "LinguaCorp primary product is ContextIQ which compresses context tokens.\n"
    "In 2024 LinguaCorp achieved an annual revenue of 15 million dollars.\n"
    "The Chief Technology Officer of LinguaCorp is Dr. Marcus Vance.\n"
    "The engineering team operates out of the Austin research campus.\n"
    "ContextIQ reduces LLM inference cost by up to 60 percent.\n"
    "The company has 45 full time employees as of 2024."
)

MD_DOC_CONTENT = (
    "# LinguaCorp Corporate Profile\n\n"
    "## Corporate Information\n"
    "LinguaCorp was founded in 2021 by Sarah Chen.\n"
    "The company headquarters is located in Austin, Texas.\n\n"
    "## Product Portfolio\n"
    "LinguaCorp primary product is ContextIQ which compresses context tokens.\n"
    "ContextIQ reduces LLM inference cost by up to 60 percent.\n\n"
    "## Financial Performance and Workforce\n"
    "In 2024 LinguaCorp achieved an annual revenue of 15 million dollars.\n"
    "The company has 45 full time employees as of 2024.\n\n"
    "## Executive Leadership and Operations\n"
    "The Chief Technology Officer of LinguaCorp is Dr. Marcus Vance.\n"
    "The engineering team operates out of the Austin research campus."
)

CSV_DOC_CONTENT = (
    "ID,Attribute,Category,Value,Year,Location\n"
    "1,Founder,Corporate Information,Sarah Chen,2021,Austin Texas\n"
    "2,Headquarters,Location,Austin Texas,2021,Austin Texas\n"
    "3,Primary Product,Product Portfolio,ContextIQ,2021,Austin Texas\n"
    "4,Cost Reduction,Product Benefits,60 percent,2024,Austin Texas\n"
    "5,Annual Revenue,Financials,15 million dollars,2024,Austin Texas\n"
    "6,Workforce,Human Resources,45 full time employees,2024,Austin Texas\n"
    "7,Chief Technology Officer,Leadership,Dr. Marcus Vance,2024,Austin Texas\n"
    "8,Engineering Campus,Operations,Austin research campus,2024,Austin Texas"
)

PLACEMENT_CSV_CONTENT = "cgpa,package\n4.73,3.5\n8.62,12.0\n7.57,8.0\n6.40,5.5\n9.10,18.0\n5.20,4.0"

BENCHMARK_DOCS: Dict[str, bytes] = {
    "benchmark_doc.txt": TXT_DOC_CONTENT.encode("utf-8"),
    "benchmark_doc.md":  MD_DOC_CONTENT.encode("utf-8"),
    "benchmark_doc.csv": CSV_DOC_CONTENT.encode("utf-8"),
    "placement.csv":     PLACEMENT_CSV_CONTENT.encode("utf-8"),
}


# ===========================================================================
# Console helpers
# ===========================================================================

def _bar(frac: float, w: int = 18) -> str:
    """Simple ASCII progress bar."""
    filled = int(round(frac * w))
    return "[" + "#" * filled + "." * (w - filled) + "]"


def _section(title: str, w: int = 76) -> None:
    print("\n" + "=" * w)
    print(f"  {title}")
    print("=" * w)


def _sub(title: str, w: int = 76) -> None:
    print(f"\n{'-' * w}\n  {title}\n{'-' * w}")


# ===========================================================================
# Similarity
# ===========================================================================

def compute_string_similarity(a: str, b: str) -> float:
    """Fuzzy string similarity via difflib SequenceMatcher."""
    if not a or not b:
        return 0.0
    return round(
        difflib.SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio(), 4
    )


# ===========================================================================
# Document ingestion
# ===========================================================================

def ensure_benchmark_documents(force_reingest: bool = False) -> None:
    """
    Ingests benchmark documents into the DocumentManager if missing.
    With force_reingest=True, always re-ingests (increments doc_version).
    """
    from backend.documents.manager import get_document_manager  # type: ignore

    doc_mgr = get_document_manager()
    for doc_id, data in BENCHMARK_DOCS.items():
        existing = doc_mgr.get_document(doc_id)
        if existing and not force_reingest:
            print(f"  ok  {doc_id:32s} already indexed (v{existing.doc_version})")
            continue
        try:
            doc_mgr.process_and_store_document(
                filename=doc_id, file_bytes=data, custom_doc_id=doc_id
            )
            action = "re-ingested" if existing else "ingested"
            print(f"  ok  {doc_id:32s} {action}")
        except Exception as exc:
            err = str(exc).lower()
            if "already" in err or "exists" in err:
                print(f"  ok  {doc_id:32s} already exists (skipped)")
            else:
                print(f"  ERR {doc_id:32s} FAILED: {exc}")


# ===========================================================================
# Cache-hit heuristic
# ===========================================================================

def _cache_hit_heuristic(pipeline_res: Dict[str, Any]) -> bool:
    """
    Infers whether the ingest cache was warm for this query.
    The pipeline does not expose a 'cache_hit' key at query-time; this
    heuristic treats retrieval_latency_ms < 300ms with non-zero compressed
    context as a warm-cache signal.
    """
    if "cache_hit" in pipeline_res:
        return bool(pipeline_res["cache_hit"])
    ret_ms = float(pipeline_res.get("retrieval_latency_ms", 9999.0))
    comp   = int(pipeline_res.get("compressed_tokens", 0))
    return ret_ms < 300 and comp > 0


# ===========================================================================
# Core per-question evaluation
# ===========================================================================

def evaluate_question_path(
    q_item: Dict[str, Any],
    bypass_compression: bool,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates one benchmark question through guarded_query_pipeline and
    records all required metrics.  Returns a flat results dict.

    bypass_compression=True  -> Path A (raw RAG, no LLMLingua compression)
    bypass_compression=False -> Path B (full CacheLingua pipeline)
    """
    from backend.guardrail.pipeline import guarded_query_pipeline  # type: ignore

    doc_id             = q_item["doc_id"]
    question           = q_item["question"]
    expected_answer    = q_item.get("expected_answer", "")
    expected_facts     = q_item.get("expected_facts", [])
    ground_truth_chunk = q_item.get("ground_truth_chunk", "")
    is_absent          = q_item.get("is_absent", False)
    is_csv             = q_item.get("is_csv", False)
    expected_csv_match = q_item.get("expected_csv_match")

    # --- Dry-run stub ---
    if dry_run:
        return {
            "answer": "[DRY RUN]",
            "answer_status": "dry_run",
            "recall_at_k":          1.0 if is_absent else 0.9,
            "precision_at_k":       0.5,
            "answer_correctness":   0.0,
            "grounding_score":      0.0,
            "flagged_hallucinated": False,
            "total_latency_ms":     0.0,
            "original_tokens":      100,
            "compressed_tokens":    100 if bypass_compression else 70,
            "tokens_saved":         0   if bypass_compression else 30,
            "compression_ratio":    1.0 if bypass_compression else 0.7,
            "cache_hit":            False,
            "csv_exact_match":      0.0 if is_csv else None,
        }

    # --- Live pipeline call ---
    pipeline_res = guarded_query_pipeline(
        doc_id=doc_id,
        question=question,
        k=10,
        top_n=5,
        bypass_compression=bypass_compression,
    )

    answer               = pipeline_res.get("answer") or ""
    answer_lower         = answer.lower()
    answer_status        = pipeline_res.get("answer_status", "unknown")
    retrieved_candidates = pipeline_res.get("retrieved_candidates") or []

    # --- 1. Retrieval Recall@K ---
    if is_absent:
        recall_at_k = 1.0
    else:
        ret_text = " ".join(
            c.get("compressed_text", "") + " " + c.get("original_text", "")
            for c in retrieved_candidates
        ).lower()

        if ground_truth_chunk and ground_truth_chunk.lower() in ret_text:
            recall_at_k = 1.0
        elif expected_facts:
            n_found = sum(1 for f in expected_facts if f.lower() in ret_text)
            recall_at_k = round(n_found / len(expected_facts), 4)
        else:
            recall_at_k = 1.0 if retrieved_candidates else 0.0

    # --- 2. Retrieval Precision@K ---
    if is_absent or not retrieved_candidates:
        precision_at_k = 1.0 if is_absent else 0.0
    elif not expected_facts:
        precision_at_k = 1.0
    else:
        rel = sum(
            1 for c in retrieved_candidates
            if any(
                f.lower() in (c.get("compressed_text", "") + " " + c.get("original_text", "")).lower()
                for f in expected_facts
            )
        )
        precision_at_k = round(rel / len(retrieved_candidates), 4)

    # --- 3. Answer Correctness ---
    if is_absent:
        fallback_phrases = [
            "don't have enough information", "does not mention", "not mentioned",
            "not specified", "not provided", "no information",
            "not explicitly stated", "no record found", "cannot find", "unable to find",
        ]
        correctness = 1.0 if (
            any(p in answer_lower for p in fallback_phrases)
            or answer_status in {"insufficient_context", "no_record_found"}
        ) else 0.0
    elif expected_facts:
        fact_score  = sum(1 for f in expected_facts if f.lower() in answer_lower) / len(expected_facts)
        fuzzy_score = compute_string_similarity(answer, expected_answer)
        correctness = round(max(fact_score, fuzzy_score), 4)
    else:
        correctness = compute_string_similarity(answer, expected_answer)

    # --- 4. Grounding + Hallucination ---
    grounding_score   = float(pipeline_res.get("grounding_score", 0.0))
    actually_answered = answer_status not in {
        "insufficient_context", "no_record_found", "blocked", "dry_run", "error"
    }
    is_hallucinated   = actually_answered and grounding_score < HALLUCINATION_THRESHOLD

    # --- 5. Token metrics ---
    orig_tokens  = int(pipeline_res.get("original_tokens", 0))
    comp_tokens  = int(pipeline_res.get("compressed_tokens", 0))
    tokens_saved = int(pipeline_res.get("tokens_saved", 0))
    comp_ratio   = float(pipeline_res.get("compression_ratio", 1.0))
    # Path A: bypass means no compression, so compressed == original
    if bypass_compression and comp_tokens == 0 and orig_tokens > 0:
        comp_tokens = orig_tokens

    # --- 6. Cache hit ---
    cache_hit = _cache_hit_heuristic(pipeline_res)

    # --- 7. CSV exact-match ---
    csv_exact_match: Optional[float] = None
    if is_csv:
        if expected_csv_match is None:
            # Absent CSV: correct iff pipeline returned a "not found" status
            csv_exact_match = 1.0 if answer_status in {
                "no_record_found", "insufficient_context"
            } else 0.0
        else:
            # Present CSV: correct iff expected value appears verbatim in answer
            csv_exact_match = 1.0 if str(expected_csv_match).lower() in answer_lower else 0.0

    return {
        "answer":             answer,
        "answer_status":      answer_status,
        "recall_at_k":        recall_at_k,
        "precision_at_k":     precision_at_k,
        "answer_correctness": correctness,
        "grounding_score":    grounding_score,
        "flagged_hallucinated": is_hallucinated,
        "total_latency_ms":   float(pipeline_res.get("total_latency_ms", 0.0)),
        "original_tokens":    orig_tokens,
        "compressed_tokens":  comp_tokens,
        "tokens_saved":       tokens_saved,
        "compression_ratio":  comp_ratio,
        "cache_hit":          cache_hit,
        "csv_exact_match":    csv_exact_match,
    }


def _error_result(msg: str) -> Dict[str, Any]:
    """Sentinel result when a pipeline call raises an exception."""
    return {
        "answer":             f"[ERROR] {msg[:100]}",
        "answer_status":      "error",
        "recall_at_k":        0.0,
        "precision_at_k":     0.0,
        "answer_correctness": 0.0,
        "grounding_score":    0.0,
        "flagged_hallucinated": False,
        "total_latency_ms":   0.0,
        "original_tokens":    0,
        "compressed_tokens":  0,
        "tokens_saved":       0,
        "compression_ratio":  1.0,
        "cache_hit":          False,
        "csv_exact_match":    None,
    }


# ===========================================================================
# Aggregate metrics
# ===========================================================================

def calculate_aggregate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes aggregate averages for one path across all benchmark questions.
    """
    n = len(results)
    if n == 0:
        return {"total_questions": 0}

    def avg(k: str) -> float:
        return sum(float(r[k]) for r in results) / n

    avg_orig = avg("original_tokens")
    avg_comp = avg("compressed_tokens")
    token_red = round((1.0 - avg_comp / avg_orig) * 100, 2) if avg_orig > 0 else 0.0

    csv_items = [r["csv_exact_match"] for r in results if r["csv_exact_match"] is not None]
    csv_acc   = round(sum(csv_items) / len(csv_items) * 100, 2) if csv_items else None

    return {
        "total_questions":              n,
        "avg_recall_at_k_pct":         round(avg("recall_at_k") * 100, 2),
        "avg_precision_at_k_pct":      round(avg("precision_at_k") * 100, 2),
        "avg_correctness_pct":         round(avg("answer_correctness") * 100, 2),
        "avg_grounding_score_pct":     round(avg("grounding_score") * 100, 2),
        "hallucination_rate_pct":      round(
            sum(1 for r in results if r["flagged_hallucinated"]) / n * 100, 2
        ),
        "avg_latency_ms":              round(avg("total_latency_ms"), 2),
        "avg_original_tokens":         round(avg_orig, 1),
        "avg_tokens_sent_llm":         round(avg_comp, 1),
        "avg_tokens_saved":            round(avg("tokens_saved"), 1),
        "avg_token_reduction_pct":     token_red,
        "avg_compression_ratio":       round(avg("compression_ratio"), 4),
        "cache_hit_rate_pct":          round(
            sum(1 for r in results if r["cache_hit"]) / n * 100, 2
        ),
        "csv_exact_match_accuracy_pct": csv_acc,
    }


# ===========================================================================
# Markdown summary
# ===========================================================================

def _delta(a: Any, b: Any, sfx: str = "") -> str:
    try:
        return f"{float(b) - float(a):+.2f}{sfx}"
    except Exception:
        return "---"


def generate_markdown_summary(
    sa: Dict[str, Any],
    sb: Dict[str, Any],
    run_ts: str,
) -> str:
    """Generates a pitch-deck-ready markdown table comparing Path A vs Path B."""
    csv_a   = f"{sa.get('csv_exact_match_accuracy_pct')}%" if sa.get("csv_exact_match_accuracy_pct") is not None else "N/A"
    csv_b   = f"{sb.get('csv_exact_match_accuracy_pct')}%" if sb.get("csv_exact_match_accuracy_pct") is not None else "N/A"
    csv_d   = (
        _delta(sa["csv_exact_match_accuracy_pct"], sb["csv_exact_match_accuracy_pct"], "%")
        if (sa.get("csv_exact_match_accuracy_pct") is not None and sb.get("csv_exact_match_accuracy_pct") is not None)
        else "---"
    )

    lines = [
        "# ContextIQ Benchmark Results: Path A (Raw RAG) vs Path B (CacheLingua / ContextIQ)",
        "",
        f"> Generated: {run_ts}  |  Questions: {sa['total_questions']}",
        "",
        "Comparing **Uncompressed Raw RAG (Path A)** against the full "
        "**CacheLingua / ContextIQ pipeline (Path B)** across 45 benchmark questions "
        "(TXT, Markdown, CSV document types).",
        "",
        "| Metric | Path A Raw RAG | Path B ContextIQ | Delta |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Questions evaluated** | {sa['total_questions']} | {sb['total_questions']} | --- |",
        f"| **Retrieval Recall@K** | {sa['avg_recall_at_k_pct']}% | {sb['avg_recall_at_k_pct']}% | {_delta(sa['avg_recall_at_k_pct'], sb['avg_recall_at_k_pct'], '%')} |",
        f"| **Retrieval Precision@K** | {sa['avg_precision_at_k_pct']}% | {sb['avg_precision_at_k_pct']}% | {_delta(sa['avg_precision_at_k_pct'], sb['avg_precision_at_k_pct'], '%')} |",
        f"| **Answer Correctness** | {sa['avg_correctness_pct']}% | {sb['avg_correctness_pct']}% | {_delta(sa['avg_correctness_pct'], sb['avg_correctness_pct'], '%')} |",
        f"| **Grounding Score** | {sa['avg_grounding_score_pct']}% | {sb['avg_grounding_score_pct']}% | {_delta(sa['avg_grounding_score_pct'], sb['avg_grounding_score_pct'], '%')} |",
        f"| **Hallucination Rate** | {sa['hallucination_rate_pct']}% | {sb['hallucination_rate_pct']}% | {_delta(sa['hallucination_rate_pct'], sb['hallucination_rate_pct'], '%')} |",
        f"| **Avg Tokens to LLM (raw / uncompressed)** | {sa['avg_tokens_sent_llm']} tokens | --- | --- |",
        f"| **Avg Tokens to LLM (after compression)** | --- | {sb['avg_tokens_sent_llm']} tokens | **{sb['avg_token_reduction_pct']}% reduction** |",
        f"| **Avg Tokens Saved per Query** | 0 | {sb['avg_tokens_saved']} | {_delta(0, sb['avg_tokens_saved'], ' tok')} |",
        f"| **Avg Compression Ratio** | 1.00x | {sb['avg_compression_ratio']}x | {_delta(1.0, sb['avg_compression_ratio'], 'x')} |",
        f"| **CSV Exact-Match Accuracy** | {csv_a} | {csv_b} | {csv_d} |",
        f"| **Average Total Latency** | {sa['avg_latency_ms']} ms | {sb['avg_latency_ms']} ms | {_delta(sa['avg_latency_ms'], sb['avg_latency_ms'], ' ms')} |",
        f"| **Cache Hit Rate** | {sa['cache_hit_rate_pct']}% | {sb['cache_hit_rate_pct']}% | {_delta(sa['cache_hit_rate_pct'], sb['cache_hit_rate_pct'], '%')} |",
        "",
        "## Key Takeaways",
        "",
        f"1. **Token Cost Savings**: CacheLingua (Path B) sent **{sb['avg_tokens_sent_llm']} tokens** "
        f"to the LLM vs **{sa['avg_tokens_sent_llm']} tokens** for raw RAG -- "
        f"a **{sb['avg_token_reduction_pct']}% reduction** in inference cost per query.",
        f"2. **Answer Quality**: Path B achieved **{sb['avg_correctness_pct']}% answer correctness** "
        f"and **{sb['avg_grounding_score_pct']}% grounding score** on the 45-question benchmark.",
        f"3. **Structured CSV Retrieval**: CSV exact-match accuracy was **{csv_b}** "
        "using the hybrid structured-lookup routing path.",
        f"4. **Hallucination Control**: Hallucination rate was **{sb['hallucination_rate_pct']}%** "
        f"for Path B vs **{sa['hallucination_rate_pct']}%** for raw RAG.",
        f"5. **Latency**: Path B averaged **{sb['avg_latency_ms']} ms** end-to-end "
        f"vs **{sa['avg_latency_ms']} ms** for raw RAG.",
    ]
    return "\n".join(lines)


# ===========================================================================
# Main runner
# ===========================================================================

def run_benchmark(force_reingest: bool = False, dry_run: bool = False) -> None:
    run_ts = time.strftime("%Y-%m-%d %H:%M:%S")

    _section("CONTEXTIQ BENCHMARK SUITE: PATH A (RAW) vs PATH B (CACHELINGUA)")
    print(f"  Run timestamp : {run_ts}")
    print(f"  Benchmark file: {BENCHMARK_QA_FILE}")
    print(f"  Mode          : {'DRY RUN (no LLM calls)' if dry_run else 'LIVE'}")
    print(f"  Force reingest: {force_reingest}")

    if not os.path.exists(BENCHMARK_QA_FILE):
        print(f"\nERROR: Benchmark QA file not found: {BENCHMARK_QA_FILE}")
        sys.exit(1)

    with open(BENCHMARK_QA_FILE, "r", encoding="utf-8") as fh:
        qa_data = json.load(fh)

    total_q     = len(qa_data)
    csv_q_count = sum(1 for q in qa_data if q.get("is_csv"))
    txt_q_count = sum(1 for q in qa_data if q.get("doc_type") == "txt")
    md_q_count  = sum(1 for q in qa_data if q.get("doc_type") == "md")
    print(f"\n  Benchmark: {total_q} questions  "
          f"(TXT={txt_q_count}, MD={md_q_count}, CSV={csv_q_count})")

    # Step 1: Ensure documents are indexed
    _sub("Step 1 -- Document Ingestion")
    ensure_benchmark_documents(force_reingest=force_reingest)

    # Step 2: Evaluate
    _sub("Step 2 -- Benchmark Evaluation (45 questions x 2 paths)")
    if not dry_run:
        print("  NOTE: Each LLM call takes 1-10 s. Total: ~90 API calls.\n")

    path_a_results: List[Dict[str, Any]] = []
    path_b_results: List[Dict[str, Any]] = []
    comparisons:    List[Dict[str, Any]] = []
    t_wall = time.perf_counter()

    for idx, item in enumerate(qa_data, start=1):
        q_id     = item["id"]
        q_text   = item["question"]
        doc_type = item.get("doc_type", "?")
        is_csv   = item.get("is_csv", False)
        category = item.get("category", "?")
        frac     = idx / total_q
        q_disp   = q_text[:53] + ("..." if len(q_text) > 53 else "")

        print(f"{_bar(frac)} [{idx:02d}/{total_q}] {q_id} [{doc_type}] {q_disp}")

        # --- Path A: Raw RAG (bypass compression) ---
        try:
            res_a = evaluate_question_path(item, bypass_compression=True, dry_run=dry_run)
        except Exception as exc:
            print(f"  ! Path A error: {exc}")
            logger.debug("Path A traceback:\n%s", traceback.format_exc())
            res_a = _error_result(str(exc))
        path_a_results.append(res_a)

        if not dry_run:
            time.sleep(0.5)  # Rate-limit courtesy pause

        # --- Path B: CacheLingua / ContextIQ Pipeline ---
        try:
            res_b = evaluate_question_path(item, bypass_compression=False, dry_run=dry_run)
        except Exception as exc:
            print(f"  ! Path B error: {exc}")
            logger.debug("Path B traceback:\n%s", traceback.format_exc())
            res_b = _error_result(str(exc))
        path_b_results.append(res_b)

        if not dry_run:
            time.sleep(0.3)

        # Per-question summary
        print(
            f"  A: tokens={res_a['compressed_tokens']:4d}          "
            f"lat={res_a['total_latency_ms']:7.0f}ms  "
            f"correct={res_a['answer_correctness']:.2f}  "
            f"grnd={res_a['grounding_score']:.2f}  "
            f"cache={'HIT' if res_a['cache_hit'] else 'miss'}"
        )
        print(
            f"  B: tokens={res_b['compressed_tokens']:4d} cr={res_b['compression_ratio']:.3f}  "
            f"lat={res_b['total_latency_ms']:7.0f}ms  "
            f"correct={res_b['answer_correctness']:.2f}  "
            f"grnd={res_b['grounding_score']:.2f}  "
            f"cache={'HIT' if res_b['cache_hit'] else 'miss'}"
        )
        if is_csv:
            print(f"  CSV: A={res_a.get('csv_exact_match')}  B={res_b.get('csv_exact_match')}")

        comparisons.append({
            "question_id": q_id,
            "doc_id":      item["doc_id"],
            "doc_type":    doc_type,
            "category":    category,
            "question":    q_text,
            "is_csv":      is_csv,
            "is_absent":   item.get("is_absent", False),
            "path_a_raw":       res_a,
            "path_b_contextiq": res_b,
        })

    total_wall_ms = round((time.perf_counter() - t_wall) * 1000)

    # Aggregate
    sa = calculate_aggregate_metrics(path_a_results)
    sb = calculate_aggregate_metrics(path_b_results)

    # Save results.json
    payload: Dict[str, Any] = {
        "evaluation_timestamp": run_ts,
        "total_questions":      total_q,
        "total_wall_time_ms":   total_wall_ms,
        "dry_run":              dry_run,
        "aggregate_summary": {
            "path_a_raw":       sa,
            "path_b_contextiq": sb,
        },
        "per_question_results": comparisons,
    }
    os.makedirs(EVAL_DIR, exist_ok=True)
    with open(RESULTS_JSON_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"\n  Saved results.json       -> {RESULTS_JSON_FILE}")

    # Save results_summary.md
    with open(SUMMARY_MD_FILE, "w", encoding="utf-8") as fh:
        fh.write(generate_markdown_summary(sa, sb, run_ts))
    print(f"  Saved results_summary.md -> {SUMMARY_MD_FILE}")

    # Console comparison table
    _section("AGGREGATE COMPARISON: PATH A vs PATH B")
    cw, aw, bw = 34, 22, 22
    print(f"  {'Metric':<{cw}} | {'Path A Raw RAG':^{aw}} | {'Path B ContextIQ':^{bw}} | Delta")
    print("  " + "-" * (cw + aw + bw + 14))

    def _row(lbl: str, ka: str, kb: str, fmt: str = "{:.2f}", sfx: str = "") -> None:
        va, vb = sa.get(ka), sb.get(kb)
        va_s = (fmt.format(va) + sfx) if va is not None else "N/A"
        vb_s = (fmt.format(vb) + sfx) if vb is not None else "N/A"
        try:
            ds = f"{float(vb) - float(va):+.2f}{sfx}"
        except Exception:
            ds = "---"
        print(f"  {lbl:<{cw}} | {va_s:^{aw}} | {vb_s:^{bw}} | {ds}")

    _row("Total Questions",          "total_questions",               "total_questions",               "{:.0f}")
    _row("Retrieval Recall@K",       "avg_recall_at_k_pct",           "avg_recall_at_k_pct",           "{:.2f}", "%")
    _row("Retrieval Precision@K",    "avg_precision_at_k_pct",        "avg_precision_at_k_pct",        "{:.2f}", "%")
    _row("Answer Correctness",       "avg_correctness_pct",           "avg_correctness_pct",           "{:.2f}", "%")
    _row("Grounding Score",          "avg_grounding_score_pct",       "avg_grounding_score_pct",       "{:.2f}", "%")
    _row("Hallucination Rate",       "hallucination_rate_pct",        "hallucination_rate_pct",        "{:.2f}", "%")
    _row("Avg Tokens Sent to LLM",   "avg_tokens_sent_llm",           "avg_tokens_sent_llm",           "{:.1f}", " tok")
    _row("Token Reduction",          "avg_token_reduction_pct",       "avg_token_reduction_pct",       "{:.2f}", "%")
    _row("Avg Compression Ratio",    "avg_compression_ratio",         "avg_compression_ratio",         "{:.4f}", "x")
    _row("CSV Exact-Match Acc.",     "csv_exact_match_accuracy_pct",  "csv_exact_match_accuracy_pct",  "{:.2f}", "%")
    _row("Avg Total Latency",        "avg_latency_ms",                "avg_latency_ms",                "{:.1f}", " ms")
    _row("Cache Hit Rate",           "cache_hit_rate_pct",            "cache_hit_rate_pct",            "{:.2f}", "%")

    print(f"\n  Wall-clock: {total_wall_ms / 1000:.1f}s for {total_q * 2} pipeline calls")
    tok_red = sb.get("avg_token_reduction_pct", 0)
    print(f"  Token reduction: {tok_red}% fewer tokens sent to LLM (Path B vs A)")
    print(f"\n  Full results: {RESULTS_JSON_FILE}")
    print(f"  MD summary  : {SUMMARY_MD_FILE}\n")


# ===========================================================================
# CLI
# ===========================================================================

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m evaluation.run_benchmark",
        description=(
            "ContextIQ benchmarking suite: "
            "Path A (raw RAG) vs Path B (CacheLingua). "
            "45 questions x 2 paths."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate document setup without making LLM API calls.",
    )
    p.add_argument(
        "--force-reingest",
        action="store_true",
        default=False,
        help="Re-ingest all benchmark documents before running the benchmark.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_benchmark(force_reingest=args.force_reingest, dry_run=args.dry_run)
