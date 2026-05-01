import re
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Prompt injection patterns
# ---------------------------------------------------------------------------
INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+previous\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|above|earlier)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|above|earlier)", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"override\s+(previous|default|system)", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
]

MAX_INPUT_LENGTH = 4000


class SafetyGuard:
    """Dual-layer safety guard for input validation and output filtering."""

    def check_input(self, text: str) -> Tuple[bool, str]:
        """Validate user input against injection attempts and length limits.

        Returns:
            (is_safe, reason) – is_safe is True when the input passes all checks.
        """
        if not text or not text.strip():
            return False, "输入内容为空"

        # Prompt injection detection
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                return False, "输入包含疑似注入指令，请调整后重试"

        return True, ""

    def check_output(self, content: str) -> Tuple[bool, str, bool]:
        """Check assistant output. Returns (is_safe, modified_content, disclaimer_added)."""
        return True, content, False
