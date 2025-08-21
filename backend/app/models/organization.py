from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.user import user_organization

if TYPE_CHECKING:
    from .user import User  # noqa: F401
    from .event import Event  # noqa: F401


class Organization(Base):
    """
    Database model for organizations
    """
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    is_active = Column(Boolean(), default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship(
        "User",
        secondary=user_organization,
        back_populates="organizations"
    )
    
    events = relationship(
        "Event",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    event_series = relationship(
        "EventSeries",
        back_populates="organization",
        cascade="all, delete-orphan"
    ) 