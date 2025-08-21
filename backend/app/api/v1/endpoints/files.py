"""
File upload and management endpoints
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, get_current_active_superuser
from app.models.user import User
from app.services.file_storage import file_storage
from app.core.config import settings
from pathlib import Path

router = APIRouter()


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    category: str = Query("events", description="File category (events, users, general)"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Upload an image file
    """
    try:
        file_info = await file_storage.save_file(file, category=category, file_type="image")
        return {
            "message": "Image uploaded successfully",
            "file": file_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Query("documents", description="File category"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Upload a document file
    """
    try:
        file_info = await file_storage.save_file(file, category=category, file_type="document")
        return {
            "message": "Document uploaded successfully",
            "file": file_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{category}")
async def list_files(
    category: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    List files in a category
    """
    files = await file_storage.list_files(category, limit=limit, offset=offset)
    return {
        "files": files,
        "total": len(files),
        "limit": limit,
        "offset": offset
    }


@router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    Delete a file (superuser only)
    """
    success = await file_storage.delete_file(file_path)
    if success:
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/info/{file_path:path}")
async def get_file_info(
    file_path: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get information about a file
    """
    file_info = await file_storage.get_file_info(file_path)
    if file_info:
        return file_info
    else:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/serve/{file_path:path}")
async def serve_file(file_path: str) -> FileResponse:
    """
    Serve a file (public endpoint for media files)
    """
    full_path = Path(settings.MEDIA_ROOT) / file_path
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check - ensure file is within media root
    try:
        full_path.resolve().relative_to(Path(settings.MEDIA_ROOT).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=full_path,
        media_type="application/octet-stream",
        filename=full_path.name
    )


@router.get("/url/{file_path:path}")
async def get_file_url(
    file_path: str,
    variant: Optional[str] = Query(None, description="Image variant (thumbnail, medium, large, banner)")
) -> Any:
    """
    Get public URL for a file
    """
    url = file_storage.get_file_url(file_path, variant)
    return {"url": url}