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
    Detects if a question is asking for an exact-value or filter match against CSV columns.
    Example inputs:
      - "if cgpa is 4.73 what's the package"
      - "cgpa = 4.73"
      - "where package is 12"
      - "cgpa 4.73"

    Returns:
      {"column": "cgpa", "value": 4.73, "operator": "=="} if matched, else None.
    """
    if not question or not question.strip():
        return None

    q_lower = question.lower().strip()

    # Determine potential column names to search for
    candidate_cols = []
    if df_columns:
        for c in df_columns:
            c_str = str(c).strip()
            if c_str:
                candidate_cols.append(c_str)

    # Common generic fallback numeric column names if none provided
    if not candidate_cols:
        candidate_cols = ["cgpa", "package", "salary", "id", "score", "age", "marks", "grade", "gpa"]

    # Sort columns by length descending so longer column names match before shorter ones
    candidate_cols = sorted(set(candidate_cols), key=lambda x: len(x), reverse=True)

    # Regex patterns for matching column + numeric value
    # Operators: 'is', '=', '==', ':', 'equals', 'equal to', 'of', 'for', 'with', 'having', or plain space/juxtaposition
    for col in candidate_cols:
        col_clean = col.lower()
        col_regex = re.escape(col_clean)

        # Pattern 1: column followed by operator/word followed by number
        # e.g., "cgpa is 4.73", "cgpa = 4.73", "cgpa: 4.73", "cgpa of 4.73", "cgpa equals 4.73"
        p1 = rf"\b{col_regex}\b\s*(?:is|=|==|:|equals|equal to|of|for|with|having|@)?\s*(-?\d+(?:\.\d+)?)\b"
        m1 = re.search(p1, q_lower)
        if m1:
            try:
                val = float(m1.group(1))
                return {
                    "column": col,
                    "value": val,
                    "operator": "==",
                }
            except ValueError:
                pass

        # Pattern 2: number followed by column
        # e.g., "4.73 cgpa"
        p2 = rf"\b(-?\d+(?:\.\d+)?)\s*(?:is|=|==|:|in)?\s*\b{col_regex}\b"
        m2 = re.search(p2, q_lower)
        if m2:
            try:
                val = float(m2.group(1))
                return {
                    "column": col,
                    "value": val,
                    "operator": "==",
                }
            except ValueError:
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
    Filters a pandas DataFrame on `column` matching `value` within a numeric floating-point tolerance.
    """
    if df is None or df.empty or column not in df.columns:
        # Case-insensitive column search fallback
        matching_col = None
        for col in df.columns:
            if str(col).lower().strip() == str(column).lower().strip():
                matching_col = col
                break
        if matching_col is None:
            return pd.DataFrame()
        column = matching_col

    try:
        # Numeric conversion with coercion
        numeric_series = pd.to_numeric(df[column], errors="coerce")

        if operator == "==":
            is_match = (numeric_series - value).abs() < tolerance
        elif operator == ">":
            is_match = numeric_series > value
        elif operator == "<":
            is_match = numeric_series < value
        elif operator == ">=":
            is_match = numeric_series >= (value - tolerance)
        elif operator == "<=":
            is_match = numeric_series <= (value + tolerance)
        else:
            is_match = (numeric_series - value).abs() < tolerance

        return df[is_match.fillna(False)]
    except Exception as e:
        logger.error(f"Error filtering DataFrame on column '{column}' = {value}: {e}")
        return pd.DataFrame()
