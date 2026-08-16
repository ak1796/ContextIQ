"""
Token Counting and Estimation Module for ContextIQ.

Uses tiktoken BPE tokenizer (`cl100k_base`) as a robust local proxy for
Llama-3/Groq BPE token counting.

Methodology Note:
If exact Groq Llama-3 tokenizer files are not stored locally, tiktoken BPE is used
as a close local proxy (~4 chars/token). Exact prompt and completion token counts
are returned directly from Groq API response usage metadata when calls are executed.
"""

import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

_TIKTOKEN_ENCODER = None


def _get_encoder():
    """Lazy loader for tiktoken cl100k_base encoder."""
    global _TIKTOKEN_ENCODER
    if _TIKTOKEN_ENCODER is None:
        try:
            import tiktoken
            _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Could not load tiktoken cl100k_base: {e}. Falling back to character-ratio estimation.")
            _TIKTOKEN_ENCODER = False
    return _TIKTOKEN_ENCODER


def count_tokens(text: str) -> int:
    """
    Counts estimated tokens in a text string.
    
    Uses tiktoken cl100k_base BPE encoder when available.
    Fallback: math.ceil(len(text) / 4.0).
    """
    if not text:
        return 0
    
    encoder = _get_encoder()
    if encoder:
        try:
            return len(encoder.encode(text))
        except Exception as e:
            logger.debug(f"tiktoken encoding failed: {e}, falling back to character estimation.")
    
    # Fallback heuristic: ~4 characters per token
    return math.ceil(len(text) / 4.0)


def count_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """
    Estimates total token count for a list of chat completion messages.
    
    Includes per-message metadata/structure overhead (role tags + message boundaries).
    """
    if not messages:
        return 0
    
    total = 3  # Base chat priming tokens (<|im_start|>system...)
    for msg in messages:
        total += 4  # Formatting overhead per message
        content = msg.get("content", "")
        role = msg.get("role", "")
        total += count_tokens(content)
        total += count_tokens(role)
        
    return total
