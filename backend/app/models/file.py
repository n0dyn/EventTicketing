"""
File model for storing file metadata
"""
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class File(Base):
    """Model for storing file metadata"""
    
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=True)
    content_type = Column(String(100), nullable=False)
    size = Column(BigInteger, nullable=False)  # File size in bytes
    category = Column(String(50), nullable=False, index=True)  # events, users, documents, etc.
    file_type = Column(String(20), nullable=False)  # image, document, etc.
    path = Column(String(500), nullable=False, unique=True)  # Relative path to file
    url = Column(String(500), nullable=False)  # Public URL
    variants = Column(Text, nullable=True)  # JSON string of variants (for images)
    
    # Optional association with user who uploaded
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    uploaded_by = relationship("User", back_populates="uploaded_files")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', category='{self.category}')>"