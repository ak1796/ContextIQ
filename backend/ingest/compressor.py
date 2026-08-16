import re
import csv
import io
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

_COMPRESSOR_INSTANCE = None


def _get_compressor():
    global _COMPRESSOR_INSTANCE
    if _COMPRESSOR_INSTANCE is None:
        from llmlingua import PromptCompressor
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            _COMPRESSOR_INSTANCE = PromptCompressor(
                model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
                use_llmlingua2=True,
                device_map=device,
            )
        except Exception as e:
            logger.warning(f"Could not load bert-base llmlingua-2 model: {e}. Trying xlm-roberta model.")
            _COMPRESSOR_INSTANCE = PromptCompressor(
                model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
                use_llmlingua2=True,
                device_map=device,
            )
    return _COMPRESSOR_INSTANCE


def split_into_sentences(text: str) -> List[str]:
    """Split input text into coherent paragraph/sentence-level chunks for plain text (.txt)."""
    if not text or not text.strip():
        return []

    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks = []
    current_chunk = []

    for line in raw_lines:
        parts = re.split(r'(?<=[.!?])\s+', line)
        for part in parts:
            part = part.strip()
            if part:
                current_chunk.append(part)
                if len(current_chunk) >= 2 or len(" ".join(current_chunk).split()) >= 30:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks if chunks else [text.strip()]


def split_csv_into_chunks(text: str, doc_id: str = "") -> List[str]:
    """
    Parses CSV text and converts each row into a self-contained sentence,
    associating column headers and document entity name directly with cell values.
    """
    if not text or not text.strip():
        return []

    chunks = []
    doc_label = doc_id.split('.')[0].split('/')[-1].split('\\')[-1] if doc_id else ""
    doc_prefix = f"Entity: {doc_label} | " if doc_label else ""

    try:
        reader = csv.reader(io.StringIO(text.strip()))
        rows = [r for r in reader if r]
        if not rows:
            return []

        headers = [h.strip() for h in rows[0]]
        for idx, row in enumerate(rows[1:], start=1):
            pairs = []
            for h, v in zip(headers, row):
                h_clean = h.strip()
                v_clean = v.strip()
                if h_clean and v_clean:
                    pairs.append(f"{h_clean}: {v_clean}")
            if pairs:
                row_str = f"{doc_prefix}Record {idx}: " + ", ".join(pairs)
                chunks.append(row_str)
    except Exception as e:
        logger.warning(f"Error parsing CSV content: {e}. Falling back to standard line splitting.")
        return split_into_sentences(text)

    return chunks if chunks else split_into_sentences(text)


def split_markdown_into_chunks(text: str) -> List[str]:
    """
    Parses Markdown text while maintaining active heading context hierarchy
    for each paragraph or sentence chunk.
    """
    if not text or not text.strip():
        return []

    heading_stack = []
    chunks = []

    lines = text.splitlines()
    buffer = []

    def flush_buffer(heading_path: str):
        if not buffer:
            return
        para = " ".join(buffer).strip()
        buffer.clear()
        if not para:
            return
        parts = re.split(r'(?<=[.!?])\s+', para)
        current = []
        for part in parts:
            part = part.strip()
            if part:
                current.append(part)
                if len(current) >= 2 or len(" ".join(current).split()) >= 30:
                    sentence_grp = " ".join(current)
                    if heading_path:
                        chunks.append(f"[{heading_path}] {sentence_grp}")
                    else:
                        chunks.append(sentence_grp)
                    current = []
        if current:
            sentence_grp = " ".join(current)
            if heading_path:
                chunks.append(f"[{heading_path}] {sentence_grp}")
            else:
                chunks.append(sentence_grp)

    for line in lines:
        line_str = line.strip()
        if not line_str:
            heading_path = " > ".join(heading_stack)
            flush_buffer(heading_path)
            continue

        header_match = re.match(r'^(#{1,6})\s+(.+)$', line_str)
        if header_match:
            heading_path = " > ".join(heading_stack)
            flush_buffer(heading_path)

            level = len(header_match.group(1))
            heading_title = header_match.group(2).strip()

            heading_stack = heading_stack[:level - 1]
            heading_stack.append(heading_title)
        else:
            buffer.append(line_str)

    heading_path = " > ".join(heading_stack)
    flush_buffer(heading_path)

    return chunks if chunks else split_into_sentences(text)


def compress_document(text: str, doc_id: str, rate: float = 0.75) -> List[Dict[str, Any]]:
    """
    Runs format-aware chunking and optional LLMLingua-2 compression on document text.
    - CSV files: Header-value annotated row chunks with document entity context.
    - Markdown files: Section-path hierarchy annotated paragraph chunks.
    - TXT files: Sentence/paragraph chunks with context-aware LLMLingua-2 compression.
    """
    doc_id_lower = doc_id.lower()

    is_csv = doc_id_lower.endswith('.csv')
    is_md = doc_id_lower.endswith('.md') or doc_id_lower.endswith('.markdown')

    if is_csv:
        sentences = split_csv_into_chunks(text, doc_id=doc_id)
        is_tabular = True
    elif is_md:
        sentences = split_markdown_into_chunks(text)
        is_tabular = False
    else:
        sentences = split_into_sentences(text)
        is_tabular = False

    if not sentences:
        return []

    compressor = None
    if not is_tabular:
        try:
            compressor = _get_compressor()
        except Exception as err:
            logger.warning(f"LLMLingua-2 compressor initialization failed: {err}. Using fallback compression.")

    chunks = []
    for idx, sentence in enumerate(sentences):
        token_count_before = len(sentence.split())

        if compressor is not None and not is_tabular:
            try:
                header_prefix = ""
                content_to_compress = sentence
                if sentence.startswith("[") and "]" in sentence:
                    closing_bracket_idx = sentence.index("]")
                    header_prefix = sentence[:closing_bracket_idx + 1] + " "
                    content_to_compress = sentence[closing_bracket_idx + 1:].strip()

                res = compressor.compress_prompt(
                    [content_to_compress],
                    rate=rate,
                    drop_consecutive=True,
                )

                compressed_body = res.get("compressed_prompt", content_to_compress)
                compressed_text = f"{header_prefix}{compressed_body}".strip()

                if "origin_tokens" in res and "compressed_tokens" in res:
                    token_count_before = res["origin_tokens"]
                    token_count_after = res["compressed_tokens"]
                else:
                    token_count_after = len(compressed_text.split())
            except Exception as e:
                logger.warning(f"Error compressing sentence {idx}: {e}")
                compressed_text = sentence
                token_count_after = token_count_before
        else:
            compressed_text = sentence
            token_count_after = token_count_before

        chunks.append({
            "chunk_index": idx,
            "original_text": sentence,
            "compressed_text": compressed_text,
            "token_count_before": token_count_before,
            "token_count_after": token_count_after,
        })

    return chunks
