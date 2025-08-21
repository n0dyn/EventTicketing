"""
File storage service for handling uploads and media management
"""
import logging
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional, List, Dict, Any
from datetime import datetime

from fastapi import UploadFile, HTTPException
from PIL import Image, ImageOps
import aiofiles

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileStorageService:
    """Service for handling file uploads and storage"""
    
    # Supported file types
    SUPPORTED_IMAGE_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif"
    }
    
    SUPPORTED_DOCUMENT_TYPES = {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls"
    }
    
    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Image processing settings
    IMAGE_SIZES = {
        "thumbnail": (150, 150),
        "medium": (400, 400),
        "large": (800, 800),
        "banner": (1200, 400)
    }
    
    def __init__(self):
        self.base_storage_path = Path(settings.MEDIA_ROOT)
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_extension(self, content_type: str, file_type: str = "image") -> str:
        """Get file extension from content type"""
        if file_type == "image":
            return self.SUPPORTED_IMAGE_TYPES.get(content_type, ".jpg")
        else:
            return self.SUPPORTED_DOCUMENT_TYPES.get(content_type, ".bin")
    
    def _validate_file(self, file: UploadFile, file_type: str = "image") -> None:
        """Validate uploaded file"""
        if file_type == "image":
            if file.content_type not in self.SUPPORTED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image format. Supported formats: {', '.join(self.SUPPORTED_IMAGE_TYPES.keys())}"
                )
            max_size = self.MAX_IMAGE_SIZE
        else:
            if file.content_type not in self.SUPPORTED_DOCUMENT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported document format. Supported formats: {', '.join(self.SUPPORTED_DOCUMENT_TYPES.keys())}"
                )
            max_size = self.MAX_DOCUMENT_SIZE
        
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size too large. Maximum size: {max_size / (1024*1024):.1f}MB"
            )
    
    def _generate_filename(self, original_filename: str, content_type: str, file_type: str = "image") -> str:
        """Generate unique filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = self._get_file_extension(content_type, file_type)
        
        # Clean original filename
        name_part = Path(original_filename).stem[:20] if original_filename else "file"
        name_part = "".join(c for c in name_part if c.isalnum() or c in "-_")
        
        return f"{timestamp}_{unique_id}_{name_part}{extension}"
    
    def _get_storage_path(self, category: str, filename: str) -> Path:
        """Get full storage path for a file"""
        # Organize files by category and date
        date_folder = datetime.now().strftime("%Y/%m")
        return self.base_storage_path / category / date_folder / filename
    
    async def save_file(
        self, 
        file: UploadFile, 
        category: str = "uploads",
        file_type: str = "image"
    ) -> Dict[str, Any]:
        """Save uploaded file to storage"""
        try:
            # Validate file
            self._validate_file(file, file_type)
            
            # Generate filename and path
            filename = self._generate_filename(file.filename or "file", file.content_type or "", file_type)
            file_path = self._get_storage_path(category, filename)
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save original file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # For images, create different sizes
            variants = {}
            if file_type == "image":
                variants = await self._create_image_variants(file_path)
            
            # Get file info
            file_info = {
                "filename": filename,
                "original_filename": file.filename,
                "content_type": file.content_type,
                "size": len(content),
                "category": category,
                "file_type": file_type,
                "path": str(file_path.relative_to(self.base_storage_path)),
                "url": f"/media/{category}/{file_path.relative_to(self.base_storage_path / category)}",
                "variants": variants,
                "uploaded_at": datetime.now()
            }
            
            logger.info(f"File uploaded successfully: {filename}")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    async def _create_image_variants(self, original_path: Path) -> Dict[str, str]:
        """Create different sizes of an image"""
        variants = {}
        
        try:
            with Image.open(original_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Create variants
                for size_name, dimensions in self.IMAGE_SIZES.items():
                    variant_path = original_path.with_suffix(f"_{size_name}{original_path.suffix}")
                    
                    # Resize image maintaining aspect ratio
                    img_resized = ImageOps.fit(img, dimensions, Image.Resampling.LANCZOS)
                    img_resized.save(variant_path, quality=85, optimize=True)
                    
                    variants[size_name] = str(variant_path.relative_to(self.base_storage_path))
                    
        except Exception as e:
            logger.error(f"Failed to create image variants: {str(e)}")
            # Don't fail the whole upload if variant creation fails
        
        return variants
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file and its variants"""
        try:
            full_path = self.base_storage_path / file_path
            
            if full_path.exists():
                # Delete original file
                full_path.unlink()
                
                # Delete variants if they exist
                for size_name in self.IMAGE_SIZES.keys():
                    variant_path = full_path.with_suffix(f"_{size_name}{full_path.suffix}")
                    if variant_path.exists():
                        variant_path.unlink()
                
                logger.info(f"File deleted successfully: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a stored file"""
        try:
            full_path = self.base_storage_path / file_path
            
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            
            return {
                "path": file_path,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
                "exists": True
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {str(e)}")
            return None
    
    async def list_files(self, category: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List files in a category"""
        try:
            category_path = self.base_storage_path / category
            
            if not category_path.exists():
                return []
            
            files = []
            for file_path in category_path.rglob("*"):
                if file_path.is_file() and not file_path.name.endswith(tuple(f"_{size}.jpg" for size in self.IMAGE_SIZES.keys())):
                    stat = file_path.stat()
                    files.append({
                        "path": str(file_path.relative_to(self.base_storage_path)),
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime),
                        "url": f"/media/{file_path.relative_to(self.base_storage_path)}"
                    })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x["modified_at"], reverse=True)
            
            # Apply pagination
            return files[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to list files in category {category}: {str(e)}")
            return []
    
    def get_file_url(self, file_path: str, variant: str = None) -> str:
        """Get public URL for a file"""
        if variant and variant in self.IMAGE_SIZES:
            path_obj = Path(file_path)
            variant_path = path_obj.with_suffix(f"_{variant}{path_obj.suffix}")
            return f"/media/{variant_path}"
        
        return f"/media/{file_path}"


# Global file storage service instance
file_storage = FileStorageService()