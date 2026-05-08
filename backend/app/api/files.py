"""File download endpoint — serves generated files by UUID."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.redis import redis_pool
from app.services.file_storage import get_file_info, _is_valid_uuid, _CONTENT_TYPE_EXT

router = APIRouter()

# Reverse mapping: extension → content_type
_EXT_CONTENT_TYPE = {v: k for k, v in _CONTENT_TYPE_EXT.items()}


@router.get("/{file_id}")
async def download_file(file_id: str):
    """Download a generated file by its UUID.

    No authentication required — the UUID is unguessable and time-limited.
    Falls back to disk lookup if Redis key has expired but file still exists.
    """
    info = await get_file_info(file_id, redis_pool)

    # Fallback: Redis key expired but file still on disk
    if info is None and _is_valid_uuid(file_id):
        allowed_dir = Path(settings.FILE_DOWNLOAD_DIR).resolve()
        for ext in _CONTENT_TYPE_EXT.values():
            candidate = allowed_dir / f"{file_id}{ext}"
            if candidate.exists():
                info = {
                    "disk_path": str(candidate),
                    "filename": f"report{ext}",
                    "content_type": _EXT_CONTENT_TYPE.get(ext, "application/octet-stream"),
                }
                break

    if info is None:
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    disk_path = info["disk_path"]
    filename = info.get("filename", file_id)
    content_type = info.get("content_type", "application/octet-stream")

    # Path traversal check: ensure disk_path is within FILE_DOWNLOAD_DIR
    resolved = Path(disk_path).resolve()
    allowed_dir = Path(settings.FILE_DOWNLOAD_DIR).resolve()
    if not str(resolved).startswith(str(allowed_dir)):
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(resolved),
        filename=filename,
        media_type=content_type,
    )
