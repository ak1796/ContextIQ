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
        cls.csv_content = (
            "cgpa,package\n"
            "4.73,3.5\n"
            "8.62,12.0\n"
            "7.57,8.0\n"
            "6.40,5.5\n"
        )
        save_tabular_dataframe(cls.doc_id, cls.csv_content)

    def test_01_is_structured_lookup_classification(self):
        df_cols = ["cgpa", "package"]

        # Case 1: "if cgpa is 4.73 what's the package"
        res1 = is_structured_lookup("if cgpa is 4.73 what's the package", df_columns=df_cols)
        self.assertIsNotNone(res1)
        self.assertEqual(res1["column"].lower(), "cgpa")
        self.assertAlmostEqual(res1["value"], 4.73)

        # Case 2: "cgpa = 8.62"
        res2 = is_structured_lookup("cgpa = 8.62", df_columns=df_cols)
        self.assertIsNotNone(res2)
        self.assertEqual(res2["column"].lower(), "cgpa")
        self.assertAlmostEqual(res2["value"], 8.62)

        # Case 3: "package is 12"
        res3 = is_structured_lookup("package is 12", df_columns=df_cols)
        self.assertIsNotNone(res3)
        self.assertEqual(res3["column"].lower(), "package")
        self.assertAlmostEqual(res3["value"], 12.0)

        # Case 4: Open-ended question should return None
        res4 = is_structured_lookup("What factors affect placement in general?", df_columns=df_cols)
        self.assertIsNone(res4)

    def test_02_dataframe_storage_and_filtering(self):
        df = get_tabular_dataframe(self.doc_id)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 4)

        # Filter exact value present
        filtered_present = filter_tabular_dataframe(df, "cgpa", 4.73)
        self.assertEqual(len(filtered_present), 1)
        self.assertAlmostEqual(float(filtered_present.iloc[0]["package"]), 3.5)

        # Filter value absent
        filtered_absent = filter_tabular_dataframe(df, "cgpa", 9.99)
        self.assertTrue(filtered_absent.empty)

    def test_03_query_pipeline_absent_value_response(self):
        # Structured query where value is not in dataset
        out = guarded_query_pipeline(
            doc_id=self.doc_id,
            question="if cgpa is 9.99 what's the package",
            cache=get_cache(),
        )
        self.assertTrue(out["success"])
        self.assertEqual(out["answer_status"], "no_record_found")
        self.assertIn("No record found with cgpa", out["answer"])
        self.assertIn("9.99", out["answer"])

    def test_04_query_pipeline_structured_match_generation(self):
        # Structured query where value IS in dataset
        out = guarded_query_pipeline(
            doc_id=self.doc_id,
            question="if cgpa is 4.73 what's the package",
            cache=get_cache(),
        )
        self.assertTrue(out["success"])
        self.assertIn("selected_chunks", out)
        self.assertGreaterEqual(len(out["selected_chunks"]), 1)
        # Verify exact record content in selected chunk
        self.assertIn("4.73", out["selected_chunks"][0]["original_text"])
        self.assertIn("3.5", out["selected_chunks"][0]["original_text"])


if __name__ == "__main__":
    unittest.main()
