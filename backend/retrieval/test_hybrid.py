import os
import unittest
import pandas as pd

from backend.retrieval.hybrid import (
    is_structured_lookup,
    save_tabular_dataframe,
    get_tabular_dataframe,
    filter_tabular_dataframe,
)
from backend.guardrail.pipeline import guarded_query_pipeline
from backend.ingest.cache import get_cache


class TestHybridRetrieval(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc_id = "test_placement.csv"
        # Generate 15 rows to test multi-row truncation (top 10 cap)
        rows = ["cgpa,package"]
        for i in range(1, 16):
            rows.append(f"{5.0 + i*0.25:.2f},{i*2.0:.1f}")
        cls.csv_content = "\n".join(rows)
        save_tabular_dataframe(cls.doc_id, cls.csv_content)

    def test_01_is_structured_lookup_classification(self):
        df_cols = ["cgpa", "package"]

        # Case 1: Exact match "if cgpa is 4.73 what's the package"
        res1 = is_structured_lookup("if cgpa is 4.73 what's the package", df_columns=df_cols)
        self.assertIsNotNone(res1)
        self.assertEqual(res1["column"].lower(), "cgpa")
        self.assertEqual(res1["operator"], "==")
        self.assertAlmostEqual(res1["value"], 4.73)

        # Case 2: Greater than or equal to (10+) "which cgpa has 10+ package"
        res2 = is_structured_lookup("which cgpa has 10+ package", df_columns=df_cols)
        self.assertIsNotNone(res2)
        self.assertEqual(res2["column"].lower(), "package")
        self.assertEqual(res2["operator"], ">=")
        self.assertAlmostEqual(res2["value"], 10.0)

        # Case 3: Greater than "package greater than 15"
        res3 = is_structured_lookup("package greater than 15", df_columns=df_cols)
        self.assertIsNotNone(res3)
        self.assertEqual(res3["column"].lower(), "package")
        self.assertEqual(res3["operator"], ">")
        self.assertAlmostEqual(res3["value"], 15.0)

        # Case 4: Less than "cgpa less than 7"
        res4 = is_structured_lookup("cgpa less than 7", df_columns=df_cols)
        self.assertIsNotNone(res4)
        self.assertEqual(res4["column"].lower(), "cgpa")
        self.assertEqual(res4["operator"], "<")
        self.assertAlmostEqual(res4["value"], 7.0)

        # Case 5: Less than or equal to "package at most 8"
        res5 = is_structured_lookup("package at most 8", df_columns=df_cols)
        self.assertIsNotNone(res5)
        self.assertEqual(res5["column"].lower(), "package")
        self.assertEqual(res5["operator"], "<=")
        self.assertAlmostEqual(res5["value"], 8.0)

        # Case 6: Open-ended question should return None
        res6 = is_structured_lookup("What factors affect student placement in general?", df_columns=df_cols)
        self.assertIsNone(res6)

    def test_02_dataframe_storage_and_comparison_filtering(self):
        df = get_tabular_dataframe(self.doc_id)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 15)

        # Filter >= 10.0
        filtered_ge = filter_tabular_dataframe(df, "package", 10.0, operator=">=")
        self.assertEqual(len(filtered_ge), 11)  # rows 5..15 (packages 10.0..30.0)

        # Filter < 6.0
        filtered_lt = filter_tabular_dataframe(df, "cgpa", 6.0, operator="<")
        self.assertEqual(len(filtered_lt), 3)  # cgpa 5.25, 5.50, 5.75

    def test_03_query_pipeline_absent_value_response(self):
        out = guarded_query_pipeline(
            doc_id=self.doc_id,
            question="if cgpa is 99.99 what's the package",
            cache=get_cache(),
        )
        self.assertTrue(out["success"])
        self.assertEqual(out["answer_status"], "no_record_found")
        self.assertIn("No record found with cgpa", out["answer"])

    def test_04_query_pipeline_truncated_multi_row_match(self):
        # Query matching 11 rows -> top 10 cap + truncation note
        out = guarded_query_pipeline(
            doc_id=self.doc_id,
            question="which cgpa has 10+ package",
            cache=get_cache(),
        )
        self.assertTrue(out["success"])
        self.assertIn("selected_chunks", out)
        # Should include 1 truncation note chunk + top 10 record chunks = 11 total chunks
        self.assertEqual(len(out["selected_chunks"]), 11)
        self.assertIn("NOTE: Showing top 10 of 11 matching rows", out["selected_chunks"][0]["original_text"])


if __name__ == "__main__":
    unittest.main()
