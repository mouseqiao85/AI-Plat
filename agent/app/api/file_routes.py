"""File serving routes for generated files (reports, etc.)."""
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.get("/{filename:path}")
async def get_file(filename: str):
    """Serve a generated file."""
    # Sanitize filename to prevent path traversal
    filename = os.path.normpath(filename)
    if filename.startswith("..") or os.path.isabs(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    base_dir = Path(settings.GENERATED_FILES_DIR).resolve()
    file_path = (base_dir / filename).resolve()

    # Ensure the resolved path is within the generated files directory
    if not str(file_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
