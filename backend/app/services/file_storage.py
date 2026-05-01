"""File storage service for generated long reports / HTML content.

Saves content to disk, tracks TTL via Redis, and provides cleanup.
"""

import os
import re
import json
import asyncio
import time
from uuid import uuid4
from typing import Optional, Dict, Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# UUID regex for validation (prevents path traversal)
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)

# Extension mapping from content type
_CONTENT_TYPE_EXT = {
    "text/html": ".html",
    "text/markdown": ".md",
    "text/plain": ".txt",
    "application/json": ".json",
}


def _ensure_dir() -> None:
    """Create the generated files directory if it doesn't exist."""
    os.makedirs(settings.FILE_DOWNLOAD_DIR, exist_ok=True)


def _is_valid_uuid(file_id: str) -> bool:
    """Check if file_id is a valid UUID v4 string."""
    return bool(_UUID_RE.match(file_id))


async def save_generated_file(
    content: str,
    filename_hint: str,
    content_type: str,
    redis_client: Any,
) -> Dict[str, Any]:
    """Save content to a file and register in Redis with TTL.

    Returns dict with file_id, filename, content_type, size, download_url.
    """
    _ensure_dir()

    file_id = str(uuid4())
    ext = _CONTENT_TYPE_EXT.get(content_type, ".txt")
    disk_name = f"{file_id}{ext}"
    disk_path = os.path.join(settings.FILE_DOWNLOAD_DIR, disk_name)

    # Write file
    with open(disk_path, "w", encoding="utf-8") as f:
        f.write(content)

    size = os.path.getsize(disk_path)

    # Register in Redis with TTL
    redis_key = f"file_download:{file_id}"
    meta = json.dumps({
        "filename": filename_hint,
        "content_type": content_type,
        "disk_path": disk_path,
        "size": size,
    }, ensure_ascii=False)

    if redis_client is not None:
        await redis_client.set(redis_key, meta, ex=settings.FILE_DOWNLOAD_TTL)

    download_url = f"/api/v1/files/{file_id}"

    logger.info(
        "file_saved",
        file_id=file_id,
        filename=filename_hint,
        size=size,
    )

    return {
        "file_id": file_id,
        "filename": filename_hint,
        "content_type": content_type,
        "size": size,
        "download_url": download_url,
    }


async def get_file_info(file_id: str, redis_client: Any) -> Optional[Dict[str, Any]]:
    """Look up file metadata from Redis. Returns None if expired or not found."""
    if not _is_valid_uuid(file_id):
        return None

    redis_key = f"file_download:{file_id}"
    if redis_client is None:
        return None

    raw = await redis_client.get(redis_key)
    if raw is None:
        return None

    meta = json.loads(raw)
    # Verify the file still exists on disk
    if not os.path.exists(meta.get("disk_path", "")):
        return None

    return meta


async def cleanup_expired_files() -> int:
    """Scan the generated files directory and delete files without a Redis key.

    Returns the number of files deleted.
    """
    _ensure_dir()
    from app.core.redis import redis_pool

    redis_client = redis_pool
    if redis_client is None:
        return 0

    deleted = 0
    for fname in os.listdir(settings.FILE_DOWNLOAD_DIR):
        # Only consider files with UUID-like names (uuid.ext)
        base, _ = os.path.splitext(fname)
        if not _is_valid_uuid(base):
            continue

        redis_key = f"file_download:{base}"
        exists = await redis_client.exists(redis_key)
        if not exists:
            fpath = os.path.join(settings.FILE_DOWNLOAD_DIR, fname)
            try:
                os.remove(fpath)
                deleted += 1
                logger.info("cleaned_expired_file", file=fname)
            except OSError:
                pass

    return deleted


async def cleanup_loop() -> None:
    """Background coroutine: clean up expired files every 30 minutes."""
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        try:
            n = await cleanup_expired_files()
            if n > 0:
                logger.info("cleanup_expired_files", deleted=n)
        except Exception as exc:
            logger.warning("cleanup_error", error=str(exc))
