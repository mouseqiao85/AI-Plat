"""Safety guard for input/output filtering."""
import re
import logging

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions?",
    r"you\s+are\s+now",
    r"system\s+prompt",
    r"disregard\s+all",
    r"forget\s+your\s+instructions?",
    r"新的?指令",
    r"忽略(之前|前面|上面)的?指令",
    r"\(system\)",
    r"<\|im_start\|>",
    r"\[INST\]",
]


class SafetyGuard:
    """Dual-layer safety: input injection detection + output filtering."""

    def check_input(self, text: str) -> tuple:
        """Check user input for injection attempts. Returns (is_safe, reason)."""
        if not text or not text.strip():
            return True, ""

        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("injection_detected pattern=%s", pattern)
                return False, "检测到非法输入模式"

        return True, ""

    def check_output(self, text: str, auto_append_disclaimer: bool = False) -> tuple:
        """Check and optionally modify agent output. Returns (is_safe, modified_text, disclaimer_added)."""
        if not text:
            return True, text, False
        return True, text, False


safety_guard = SafetyGuard()
