"""
Output Guardrail Module for ContextIQ.

Validates generated LLM answers prior to client delivery:
- Secret & API Key leakage detection (e.g. gsk_*, sk-*).
- System prompt disclosure checks.
- Grounding & hallucination validation.
- Fallback protection against unsafe outputs.
"""

import re
import logging
from typing import List, Dict, Any, Optional

from backend.guardrail.grounding import check_grounding

logger = logging.getLogger(__name__)

# Patterns for API key / secret leakage detection in outputs
SECRET_LEAK_PATTERNS = [
    re.compile(r"gsk_[a-zA-Z0-9]{30,}", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{30,}", re.IGNORECASE),
    re.compile(r"GROQ_API_KEY\s*=\s*[^\s]+", re.IGNORECASE),
]

# Patterns for system prompt disclosure in output
SYSTEM_PROMPT_LEAK_PATTERNS = [
    re.compile(r"you\s+are\s+a\s+precise,\s+truthful,\s+and\s+concise\s+ai\s+assistant", re.IGNORECASE),
    re.compile(r"retrieved\s+context\s+is\s+untrusted\s+reference\s+material", re.IGNORECASE),
    re.compile(r"never\s+reveal\s+or\s+discuss\s+internal\s+system\s+instructions", re.IGNORECASE),
]


def validate_answer(
    answer: str,
    selected_chunks: List[Dict[str, Any]],
    question: str,
) -> Dict[str, Any]:
    """
    Validates output answer for security leaks, prompt exposure, and context grounding.

    Returns structured validation result:
    {
        "allowed": bool,
        "grounded": bool | "partial",
        "grounding_score": float,
        "risk_level": "low" | "medium" | "high",
        "reason": Optional[str]
    }
    """
    if not answer or not answer.strip():
        return {
            "allowed": False,
            "grounded": False,
            "grounding_score": 0.0,
            "risk_level": "high",
            "reason": "Generated answer is empty.",
        }

    stripped_ans = answer.strip()

    # 1. Secret leakage check
    for pattern in SECRET_LEAK_PATTERNS:
        if pattern.search(stripped_ans):
            logger.error("Output guardrail triggered: Potential API key or secret leakage detected!")
            return {
                "allowed": False,
                "grounded": False,
                "grounding_score": 0.0,
                "risk_level": "high",
                "reason": "Output validation failed due to potential secret leakage.",
            }

    # 2. System prompt disclosure check
    for pattern in SYSTEM_PROMPT_LEAK_PATTERNS:
        if pattern.search(stripped_ans):
            logger.warning("Output guardrail triggered: System prompt disclosure detected in output.")
            return {
                "allowed": False,
                "grounded": False,
                "grounding_score": 0.0,
                "risk_level": "medium",
                "reason": "Output validation failed due to system prompt exposure.",
            }

    # 3. Grounding check
    grounding_res = check_grounding(answer=stripped_ans, selected_chunks=selected_chunks)
    grounded = grounding_res["grounded"]
    grounding_score = grounding_res["grounding_score"]

    if grounded is False and grounding_score < 0.35:
        logger.warning(f"Output guardrail triggered: Low grounding score ({grounding_score}).")
        return {
            "allowed": False,
            "grounded": False,
            "grounding_score": grounding_score,
            "risk_level": "high",
            "reason": "Generated answer is not sufficiently supported by retrieved document context.",
        }

    risk_level = "low" if grounded is True else "medium"

    return {
        "allowed": True,
        "grounded": grounded,
        "grounding_score": grounding_score,
        "risk_level": risk_level,
        "reason": None,
    }
