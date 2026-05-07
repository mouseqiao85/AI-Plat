"""File download endpoint — serves generated files by UUID."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.redis import redis_pool
from app.services.file_storage import get_file_info

router = APIRouter()


@router.get("/{file_id}")
async def download_file(file_id: str):
    """Download a generated file by its UUID.

    No authentication required — the UUID is unguessable and time-limited.
    """
    info = await get_file_info(file_id, redis_pool)
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
