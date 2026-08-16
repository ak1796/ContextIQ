import os
import re
import io
import pickle
import logging
from typing import Dict, Any, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)

# Directory to persist tabular DataFrames
TABULAR_STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tabular_store")
_TABULAR_CACHE: Dict[str, pd.DataFrame] = {}


def ensure_tabular_store_dir():
    """Ensure that the tabular storage directory exists."""
    if not os.path.exists(TABULAR_STORE_DIR):
        os.makedirs(TABULAR_STORE_DIR, exist_ok=True)


def save_tabular_dataframe(doc_id: str, csv_text_or_df: Union[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    """
    Saves a DataFrame for a given doc_id into memory cache and on disk.
    If input is a CSV string, parses it with pandas first.
    """
    ensure_tabular_store_dir()
    df: Optional[pd.DataFrame] = None

    if isinstance(csv_text_or_df, pd.DataFrame):
        df = csv_text_or_df
    elif isinstance(csv_text_or_df, str):
        try:
            df = pd.read_csv(io.StringIO(csv_text_or_df.strip()))
            # Clean column names (strip whitespace)
            df.columns = [str(c).strip() for c in df.columns]
        except Exception as e:
            logger.warning(f"Failed to parse CSV string into DataFrame for doc_id '{doc_id}': {e}")
            return None

    if df is not None and not df.empty:
        _TABULAR_CACHE[doc_id] = df
        pickle_path = os.path.join(TABULAR_STORE_DIR, f"{doc_id}.pkl")
        try:
            with open(pickle_path, "wb") as f:
                pickle.dump(df, f)
            logger.info(f"Saved tabular DataFrame for doc_id '{doc_id}' ({len(df)} rows, columns: {list(df.columns)})")
        except Exception as e:
            logger.error(f"Failed to persist DataFrame pickle for doc_id '{doc_id}': {e}")
        return df

    return None


def get_tabular_dataframe(doc_id: str) -> Optional[pd.DataFrame]:
    """
    Retrieves the DataFrame for doc_id from in-memory cache or disk storage.
    """
    if doc_id in _TABULAR_CACHE:
        return _TABULAR_CACHE[doc_id]

    ensure_tabular_store_dir()
    pickle_path = os.path.join(TABULAR_STORE_DIR, f"{doc_id}.pkl")
    if os.path.exists(pickle_path):
        try:
            with open(pickle_path, "rb") as f:
                df = pickle.load(f)
            _TABULAR_CACHE[doc_id] = df
            return df
        except Exception as e:
            logger.error(f"Failed to load tabular DataFrame for doc_id '{doc_id}': {e}")

    # Fallback check: if doc_id ends with .csv and file exists in sample_docs or doc manager registry
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_docs", doc_id)
    if os.path.exists(sample_path) and doc_id.lower().endswith(".csv"):
        try:
            df = pd.read_csv(sample_path)
            df.columns = [str(c).strip() for c in df.columns]
            save_tabular_dataframe(doc_id, df)
            return df
        except Exception as e:
            logger.warning(f"Fallback CSV load failed for '{sample_path}': {e}")

    return None


def is_structured_lookup(
    question: str,
    df_columns: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Detects if a question is asking for exact-value or range/comparison match against CSV columns.
    Examples:
      - "cgpa is 4.73" -> {"column": "cgpa", "value": 4.73, "operator": "=="}
      - "which cgpa has 10+ package" -> {"column": "package", "value": 10.0, "operator": ">="}
      - "package greater than 10" -> {"column": "package", "value": 10.0, "operator": ">"}
      - "cgpa less than 7" -> {"column": "cgpa", "value": 7.0, "operator": "<"}
      - "package at most 8" -> {"column": "package", "value": 8.0, "operator": "<="}
    """
    if not question or not question.strip():
        return None

    q_lower = question.lower().strip()

    candidate_cols = []
    if df_columns:
        for c in df_columns:
            c_str = str(c).strip()
            if c_str:
                candidate_cols.append(c_str)

    if not candidate_cols:
        candidate_cols = ["cgpa", "package", "salary", "id", "score", "age", "marks", "grade", "gpa"]

    candidate_cols = sorted(set(candidate_cols), key=lambda x: len(x), reverse=True)

    # Ordered list of comparison patterns (pattern_regex, operator)
    op_patterns = [
        # >= patterns
        (r"(?:>=|at least|minimum|min|no less than)\s*(-?\d+(?:\.\d+)?)", ">="),
        (r"(-?\d+(?:\.\d+)?)\s*\+", ">="),
        (r"(-?\d+(?:\.\d+)?)\s*(?:or more|or higher|and above)", ">="),

        # > patterns
        (r"(?:>|more than|greater than|above|higher than|exceeding|over)\s*(-?\d+(?:\.\d+)?)", ">"),

        # <= patterns
        (r"(?:<=|at most|maximum|max|no more than)\s*(-?\d+(?:\.\d+)?)", "<="),
        (r"(-?\d+(?:\.\d+)?)\s*(?:or less|or lower|and below)", "<="),

        # < patterns
        (r"(?:<|less than|under|below|lower than|smaller than)\s*(-?\d+(?:\.\d+)?)", "<"),

        # == patterns
        (r"(?:==|=|is|:|\bequals\b|\bequal to\b|\bof\b|\bfor\b|\bwith\b|\bhaving\b)?\s*(-?\d+(?:\.\d+)?)", "=="),
    ]

    for col in candidate_cols:
        col_clean = col.lower()
        col_regex = re.escape(col_clean)

        for pattern, op in op_patterns:
            # Column before pattern (e.g., "package 10+", "package at least 10", "cgpa is 4.73")
            p_before = rf"\b{col_regex}\b\s*{pattern}\b"
            m_before = re.search(p_before, q_lower)
            if m_before:
                try:
                    val = float(m_before.group(1))
                    return {"column": col, "value": val, "operator": op}
                except (ValueError, IndexError):
                    pass

            # Pattern before column (e.g., "10+ package", "at least 10 package", "greater than 10 package")
            p_after = rf"\b{pattern}\s*(?:in|for|of|with)?\s*\b{col_regex}\b"
            m_after = re.search(p_after, q_lower)
            if m_after:
                try:
                    val = float(m_after.group(1))
                    return {"column": col, "value": val, "operator": op}
                except (ValueError, IndexError):
                    pass

    return None


def filter_tabular_dataframe(
    df: pd.DataFrame,
    column: str,
    value: float,
    operator: str = "==",
    tolerance: float = 0.01,
) -> pd.DataFrame:
    """
    Filters pandas DataFrame on `column` according to `operator` (>=, >, <=, <, ==).
    """
    if df is None or df.empty or column not in df.columns:
        matching_col = None
        for col in df.columns:
            if str(col).lower().strip() == str(column).lower().strip():
                matching_col = col
                break
        if matching_col is None:
            return pd.DataFrame()
        column = matching_col

    try:
        numeric_series = pd.to_numeric(df[column], errors="coerce")

        if operator == "==":
            is_match = (numeric_series - value).abs() < tolerance
        elif operator == ">=":
            is_match = numeric_series >= (value - tolerance)
        elif operator == ">":
            is_match = numeric_series > (value + 1e-9)
        elif operator == "<=":
            is_match = numeric_series <= (value + tolerance)
        elif operator == "<":
            is_match = numeric_series < (value - 1e-9)
        else:
            is_match = (numeric_series - value).abs() < tolerance

        return df[is_match.fillna(False)]
    except Exception as e:
        logger.error(f"Error filtering DataFrame on column '{column}' {operator} {value}: {e}")
        return pd.DataFrame()
