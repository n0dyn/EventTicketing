from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Column, DateTime, String, Text, 
    ForeignKey, Integer, Float, Enum, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
import enum

from app.db.base_class import Base
from app.models.event_category import event_category

if TYPE_CHECKING:
    from .user import User  # noqa: F401
    from .organization import Organization  # noqa: F401
    from .event_category import EventCategory  # noqa: F401
    from .ticket import TicketType  # noqa: F401


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Event(Base):
    """
    Database model for events
    """
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    venue = Column(String, nullable=True)
    start_time = Column("start_datetime", DateTime, nullable=False)
    end_time = Column("end_datetime", DateTime, nullable=False)
    timezone = Column(String, default="UTC", nullable=False)
    featured_image = Column(String, nullable=True)
    banner_image = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String, default="USD", nullable=False)
    is_free = Column(Boolean, default=False)
    status = Column(Enum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    is_public = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Recurring event support
    is_part_of_series = Column(Boolean, default=False)
    event_series_id = Column(Integer, ForeignKey("event_series.id"), nullable=True)
    
    owner_id = Column(String, ForeignKey("user.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organization.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="owned_events")
    organization = relationship("Organization", back_populates="events")
    categories = relationship(
        "EventCategory",
        secondary=event_category,
        back_populates="events"
    )
    ticket_types = relationship("TicketType", back_populates="event", cascade="all, delete-orphan")
    
    # Recurring event relationships
    event_series = relationship("EventSeries", back_populates="events")
    event_instance = relationship("EventInstance", back_populates="event", uselist=False)
    
    @hybrid_property
    def start_date(self):
        """Get the date portion of start_time"""
        return self.start_time.date() if self.start_time else None
    
    @hybrid_property
    def is_recurring(self):
        """Check if this event is part of a recurring series"""
        return self.is_part_of_series and self.event_series_id is not None
    
    @hybrid_property
    def has_customizations(self):
        """Check if this event instance has customizations"""
        return self.event_instance is not None 