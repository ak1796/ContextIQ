"""
Enhanced 45-Question Benchmark Evaluation Suite for CacheLingua RAG Pipeline (Phase 7.3).
Evaluates 15 questions per format (TXT, MD, CSV) across 6 question categories:
1. Direct factual
2. Multi-field
3. Numerical
4. Field relationships
5. Information absent / out-of-bounds (tests non-hallucination / fallback)
6. Multi-chunk synthesis
"""

import os
import json
import logging
from typing import List, Dict, Any

from documents.manager import get_document_manager
from guardrail.pipeline import guarded_query_pipeline

logger = logging.getLogger(__name__)

# Ground truth sample document contents
TXT_DOC_CONTENT = """LinguaCorp was founded in 2021 by Sarah Chen.
The company headquarters is located in Austin, Texas.
LinguaCorp primary product is CacheLingua which compresses context tokens.
In 2024 LinguaCorp achieved an annual revenue of 15 million dollars.
The Chief Technology Officer of LinguaCorp is Dr. Marcus Vance.
The engineering team operates out of the Austin research campus.
CacheLingua reduces LLM inference cost by up to 60 percent.
The company has 45 full time employees as of 2024."""

MD_DOC_CONTENT = """# LinguaCorp Corporate Profile

## Corporate Information
LinguaCorp was founded in 2021 by Sarah Chen.
The company headquarters is located in Austin, Texas.

## Product Portfolio
LinguaCorp primary product is CacheLingua which compresses context tokens.
CacheLingua reduces LLM inference cost by up to 60 percent.

## Financial Performance & Workforce
In 2024 LinguaCorp achieved an annual revenue of 15 million dollars.
The company has 45 full time employees as of 2024.

## Executive Leadership & Operations
The Chief Technology Officer of LinguaCorp is Dr. Marcus Vance.
The engineering team operates out of the Austin research campus."""

CSV_DOC_CONTENT = """ID,Attribute,Category,Value,Year,Location
1,Founder,Corporate Information,Sarah Chen,2021,Austin Texas
2,Headquarters,Location,Austin Texas,2021,Austin Texas
3,Primary Product,Product Portfolio,CacheLingua,2021,Austin Texas
4,Cost Reduction,Product Benefits,60 percent,2024,Austin Texas
5,Annual Revenue,Financials,15 million dollars,2024,Austin Texas
6,Workforce,Human Resources,45 full time employees,2024,Austin Texas
7,Chief Technology Officer,Leadership,Dr. Marcus Vance,2024,Austin Texas
8,Engineering Campus,Operations,Austin research campus,2024,Austin Texas"""

BENCHMARK_QUESTIONS = [
    # 1. Direct Factual
    {"id": "q1", "category": "direct_factual", "question": "Who founded LinguaCorp?", "expected_facts": ["sarah chen"], "absent": False},
    {"id": "q2", "category": "direct_factual", "question": "Where is the company headquarters?", "expected_facts": ["austin"], "absent": False},
    {"id": "q3", "category": "direct_factual", "question": "Who is the Chief Technology Officer?", "expected_facts": ["marcus vance"], "absent": False},
    
    # 2. Multi-field
    {"id": "q4", "category": "multi_field", "question": "Who founded LinguaCorp and in what year?", "expected_facts": ["sarah chen", "2021"], "absent": False},
    {"id": "q5", "category": "multi_field", "question": "Where does the engineering team operate and what is the CTO's name?", "expected_facts": ["austin", "marcus vance"], "absent": False},
    
    # 3. Numerical
    {"id": "q6", "category": "numerical", "question": "What was LinguaCorp's annual revenue in 2024?", "expected_facts": ["15 million"], "absent": False},
    {"id": "q7", "category": "numerical", "question": "How many full time employees does LinguaCorp have?", "expected_facts": ["45"], "absent": False},
    {"id": "q8", "category": "numerical", "question": "By what percentage does CacheLingua reduce inference cost?", "expected_facts": ["60"], "absent": False},
    
    # 4. Field Relationships
    {"id": "q9", "category": "field_relationships", "question": "What primary product does LinguaCorp build to compress context tokens?", "expected_facts": ["cachelingua"], "absent": False},
    {"id": "q10", "category": "field_relationships", "question": "In what year was the 15 million dollar revenue achieved?", "expected_facts": ["2024"], "absent": False},
    
    # 5. Absent Information (Out of bounds - expects fallback / non-hallucination)
    {"id": "q11", "category": "absent_info", "question": "Who is the Chief Executive Officer (CEO) of LinguaCorp?", "expected_facts": [], "absent": True},
    {"id": "q12", "category": "absent_info", "question": "What stock symbol does LinguaCorp trade under?", "expected_facts": [], "absent": True},
    {"id": "q13", "category": "absent_info", "question": "How much funding did LinguaCorp raise in Series A?", "expected_facts": [], "absent": True},
    
    # 6. Multi-chunk Synthesis
    {"id": "q14", "category": "multi_chunk", "question": "Summarize LinguaCorp's product name and its cost reduction benefit.", "expected_facts": ["cachelingua", "60"], "absent": False},
    {"id": "q15", "category": "multi_chunk", "question": "What is the company's revenue in 2024 and how many employees work there?", "expected_facts": ["15 million", "45"], "absent": False},
]


def run_benchmark():
    doc_mgr = get_document_manager()

    formats = [
        ("TXT", "benchmark_doc.txt", TXT_DOC_CONTENT.encode("utf-8")),
        ("Markdown", "benchmark_doc.md", MD_DOC_CONTENT.encode("utf-8")),
        ("CSV", "benchmark_doc.csv", CSV_DOC_CONTENT.encode("utf-8")),
    ]

    for fmt, filename, content in formats:
        doc_mgr.process_and_store_document(filename=filename, file_bytes=content, custom_doc_id=filename)

    results_table = {}
    failed_question_details = []

    for fmt, filename, _ in formats:
        total_questions = len(BENCHMARK_QUESTIONS)
        recall_hits = 0
        correct_answers = 0
        grounded_count = 0
        insufficient_count = 0
        incorrect_count = 0
        blocked_count = 0

        for q in BENCHMARK_QUESTIONS:
            q_text = q["question"]
            expected = q["expected_facts"]
            is_absent = q["absent"]

            res = guarded_query_pipeline(doc_id=filename, question=q_text, k=8, top_n=5)
            raw_ans = res.get("answer") or ""
            ans = raw_ans.lower()
            ans_status = res.get("answer_status")
            grounded = res.get("grounded", False)
            retrieved = res.get("retrieved_candidates", [])
            selected = res.get("selected_chunks", [])

            # Check Recall@K:
            if is_absent:
                recall_hit = True
                recall_hits += 1
            else:
                retrieved_all = " ".join([c.get("compressed_text", "") + " " + c.get("original_text", "") for c in retrieved]).lower()
                recall_hit = all(f in retrieved_all for f in expected)
                if recall_hit:
                    recall_hits += 1

            # Check Answer Correctness:
            if is_absent:
                # Absent questions are correct if the answer states info is missing / not mentioned
                is_fallback_phrase = any(phrase in ans for phrase in [
                    "don't have enough information",
                    "does not mention",
                    "not mentioned",
                    "not specified",
                    "not provided",
                    "no information",
                    "not explicitly stated"
                ])
                if is_fallback_phrase or ans_status == "insufficient_context":
                    is_correct = True
                    correct_answers += 1
                    insufficient_count += 1
                else:
                    is_correct = False
                    incorrect_count += 1
            else:
                is_correct = all(f in ans for f in expected)
                if is_correct:
                    correct_answers += 1
                else:
                    incorrect_count += 1
                if ans_status == "insufficient_context":
                    insufficient_count += 1

            if grounded is True or grounded == "partial":
                grounded_count += 1

            if ans_status == "blocked":
                blocked_count += 1

            if not is_correct:
                failed_question_details.append({
                    "format": fmt,
                    "question_id": q["id"],
                    "question": q_text,
                    "category": q["category"],
                    "expected_facts": expected,
                    "raw_answer": raw_ans,
                    "answer_status": ans_status,
                    "selected_chunks": [c.get("compressed_text") or c.get("original_text") for c in selected],
                })

        results_table[fmt] = {
            "questions": total_questions,
            "recall": f"{(recall_hits / total_questions) * 100:.1f}%",
            "correctness": f"{(correct_answers / total_questions) * 100:.1f}% ({correct_answers}/{total_questions})",
            "grounded": f"{(grounded_count / total_questions) * 100:.1f}% ({grounded_count}/{total_questions})",
            "insufficient": insufficient_count,
            "incorrect": incorrect_count,
            "blocked": blocked_count,
        }

    print("\n" + "=" * 85)
    print("      CACHELINGUA PHASE 7.3 ENHANCED 45-QUESTION RAG EVALUATION REPORT")
    print("=" * 85)
    print(f"{'Format':<10} | {'Questions':<10} | {'Recall@K':<12} | {'Answer Correctness':<20} | {'Grounded':<12} | {'Insufficient Context':<20}")
    print("-" * 85)
    for fmt, r in results_table.items():
        print(f"{fmt:<10} | {r['questions']:<10} | {r['recall']:<12} | {r['correctness']:<20} | {r['grounded']:<12} | {r['insufficient']:<20}")
    print("=" * 85 + "\n")

    if failed_question_details:
        print("=" * 85)
        print("                        FAILED QUESTIONS DETAILS")
        print("=" * 85)
        for fail in failed_question_details:
            print(f"Format: {fail['format']} | Q ID: {fail['question_id']} | Category: {fail['category']}")
            print(f"Question: {fail['question']}")
            print(f"Expected Facts: {fail['expected_facts']}")
            print(f"Raw Answer: {fail['raw_answer']}")
            print(f"Answer Status: {fail['answer_status']}")
            print(f"Selected Chunks: {fail['selected_chunks']}")
            print("-" * 85)
    else:
        print("SUCCESS: ALL 45 BENCHMARK QUESTIONS PASSED WITH 100% ACCURACY!\n")

    return results_table, failed_question_details


if __name__ == "__main__":
    run_benchmark()
