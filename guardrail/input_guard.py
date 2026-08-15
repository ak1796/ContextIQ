"""
Input Guardrail Module for CacheLingua.

Provides multi-layered validation for incoming user questions:
- Emptiness and whitespace checks.
- Maximum length boundary checks.
- Prompt injection, system instruction override, and secret extraction detection.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1000

# Compiled regex patterns for suspicious / malicious input patterns
INJECTION_PATTERNS = [
    # System instruction override / jailbreaks
    re.compile(r"ignore\s+(previous|prior|above|all)\s+instruction", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|prior|above|all)\s+instruction", re.IGNORECASE),
    re.compile(r"override\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now|DAN\s+mode", re.IGNORECASE),
    re.compile(r"forget\s+all\s+prior\s+rules", re.IGNORECASE),
    # System prompt disclosure
    re.compile(r"(reveal|print|show|output|display)\s+(your\s+)?system\s+(prompt|instruction|message)", re.IGNORECASE),
    re.compile(r"repeat\s+(the\s+)?system\s+(prompt|instruction)", re.IGNORECASE),
    # Secret / API Key extraction
    re.compile(r"(reveal|print|show|output|display|get)\s+(the\s+)?(api\s*key|secret|env|environment\s*variable)", re.IGNORECASE),
    re.compile(r"GROQ_API_KEY", re.IGNORECASE),
]


def validate_question(question: str) -> Dict[str, Any]:
    """
    Validates user question against security rules, length limits, and injection attacks.

    Returns structured validation response:
    {
        "allowed": bool,
        "reason": Optional[str],
        "risk_level": "low" | "medium" | "high"
    }
    """
    if not question or not question.strip():
        return {
            "allowed": False,
            "reason": "Question is empty or whitespace-only.",
            "risk_level": "high",
        }

    stripped_q = question.strip()

    if len(stripped_q) > MAX_QUESTION_LENGTH:
        return {
            "allowed": False,
            "reason": f"Question length ({len(stripped_q)} chars) exceeds maximum allowed limit of {MAX_QUESTION_LENGTH} characters.",
            "risk_level": "medium",
        }

    # Check for unprintable / malformed control characters
    if any(ord(char) < 32 and char not in "\n\r\t" for char in stripped_q):
        return {
            "allowed": False,
            "reason": "Question contains malformed control characters.",
            "risk_level": "high",
        }

    # Check prompt injection patterns
    for pattern in INJECTION_PATTERNS:
        if pattern.search(stripped_q):
            logger.warning("Input guardrail triggered: Potential prompt injection or secret extraction attempt detected.")
            return {
                "allowed": False,
                "reason": "Potential prompt injection or restricted command detected.",
                "risk_level": "high",
            }

    return {
        "allowed": True,
        "reason": None,
        "risk_level": "low",
    }
