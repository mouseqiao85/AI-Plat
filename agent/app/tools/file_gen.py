"""File generation tool: materializes long outputs as downloadable files."""
import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _detect_format(content: str) -> str:
    """Detect output format from content."""
    if re.search(r'<html|<div|<table|<p\s', content, re.IGNORECASE):
        return "html"
    if re.search(r'^#+\s|\*\*|```', content, re.MULTILINE):
        return "md"
    if re.search(r'^\w+[,\t]', content, re.MULTILINE) and content.count(",") > 5:
        return "csv"
    return "md"


def _generate_filename(session_id: str, fmt: str) -> str:
    """Generate a unique filename."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_hash = hashlib.md5(session_id.encode()).hexdigest()[:6]
    return f"output_{ts}_{short_hash}.{fmt}"


async def generate_file(
    content: str,
    session_id: str = "",
    user_id: int = 0,
    format_hint: str = "",
) -> Optional[dict]:
    """Generate a downloadable file from content.

    Returns dict with {filename, url, size, format} or None on failure.
    """
    if not content or len(content) < 100:
        return None

    fmt = format_hint or _detect_format(content)
    filename = _generate_filename(session_id or "anon", fmt)

    # Ensure output directory exists
    output_dir = Path(settings.GENERATED_FILES_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename

    try:
        # Write content with appropriate wrapping
        if fmt == "html" and not content.strip().startswith("<!DOCTYPE"):
            wrapped = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>Generated Report</title>
<style>body{{font-family:system-ui;max-width:800px;margin:2em auto;padding:0 1em;line-height:1.6}}</style>
</head>
<body>
{content}
</body>
</html>"""
            filepath.write_text(wrapped, encoding="utf-8")
        else:
            filepath.write_text(content, encoding="utf-8")

        size = filepath.stat().st_size
        # URL assumes Go gateway serves /api/v1/files/
        url = f"/api/v1/files/{filename}"

        logger.info("generated file: %s (%d bytes)", filename, size)
        return {
            "filename": filename,
            "url": url,
            "size": size,
            "format": fmt,
        }
    except Exception as e:
        logger.error("file generation failed: %s", e)
        return None
