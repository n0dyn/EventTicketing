from datetime import datetime
from typing import TYPE_CHECKING, List
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, String, Table, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .organization import Organization  # noqa: F401
    from .event import Event  # noqa: F401


# User-Organization association table
user_organization = Table(
    "user_organization",
    Base.metadata,
    Column("user_id", String, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String, nullable=False, default="member"),
)


class UserRole(str, Enum):
    """Enum for user roles in the system"""
    ADMIN = "admin"
    ORGANIZER = "organizer"
    ATTENDEE = "attendee"


class User(Base):
    """
    Database model for users
    """
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    role = Column(SQLAlchemyEnum(UserRole), nullable=False, default=UserRole.ATTENDEE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organizations = relationship(
        "Organization",
        secondary=user_organization,
        back_populates="members"
    )
    
    owned_events = relationship(
        "Event",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
    
    event_series = relationship(
        "EventSeries",
        back_populates="owner",
        cascade="all, delete-orphan"
    ) 