"""
File schemas for API validation
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class FileBase(BaseModel):
    """Base file schema"""
    filename: str = Field(..., description="File name")
    original_filename: Optional[str] = Field(None, description="Original uploaded filename")
    content_type: str = Field(..., description="MIME type")
    category: str = Field(..., description="File category")
    file_type: str = Field(..., description="File type (image, document, etc.)")


class FileCreate(FileBase):
    """Schema for creating a file record"""
    size: int = Field(..., gt=0, description="File size in bytes")
    path: str = Field(..., description="File path")
    url: str = Field(..., description="File URL")
    variants: Optional[Dict[str, str]] = Field(None, description="Image variants")
    uploaded_by_id: Optional[int] = Field(None, description="User who uploaded the file")


class FileUpdate(BaseModel):
    """Schema for updating a file record"""
    filename: Optional[str] = Field(None, description="File name")
    category: Optional[str] = Field(None, description="File category")


class FileInDB(FileBase):
    """Schema for file in database"""
    id: int
    size: int
    path: str
    url: str
    variants: Optional[Dict[str, str]] = None
    uploaded_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileResponse(FileInDB):
    """Schema for file API responses"""
    pass


class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    message: str
    file: FileResponse


class FileListResponse(BaseModel):
    """Schema for file list response"""
    files: list[FileResponse]
    total: int
    limit: int
    offset: int


class ImageVariantRequest(BaseModel):
    """Schema for requesting image variant"""
    variant: str = Field(..., description="Variant name (thumbnail, medium, large, banner)")
    
    @validator('variant')
    def validate_variant(cls, v):
        allowed_variants = ['thumbnail', 'medium', 'large', 'banner']
        if v not in allowed_variants:
            raise ValueError(f'Variant must be one of: {", ".join(allowed_variants)}')
        return v


class FileUrlResponse(BaseModel):
    """Schema for file URL response"""
    url: str = Field(..., description="File URL")


class FileInfoResponse(BaseModel):
    """Schema for file info response"""
    path: str
    size: int
    modified_at: datetime
    exists: bool