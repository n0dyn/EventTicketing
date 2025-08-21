from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, String, Text, Table, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .event import Event  # noqa: F401


# Event-Category association table
event_category = Table(
    "event_category",
    Base.metadata,
    Column("event_id", String, ForeignKey("event.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", String, ForeignKey("eventcategory.id", ondelete="CASCADE"), primary_key=True),
)


class EventCategory(Base):
    """
    Database model for event categories
    """
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship(
        "Event",
        secondary=event_category,
        back_populates="categories"
    ) 