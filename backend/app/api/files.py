"""File download endpoint — serves generated files by UUID."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

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

    return FileResponse(
        path=disk_path,
        filename=filename,
        media_type=content_type,
    )
