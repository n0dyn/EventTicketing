from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .event import Event  # noqa: F401
    from .ticket import Ticket  # noqa: F401
    from .user import User  # noqa: F401


# Event-Attendee association table for tracking attendance
event_attendee = Table(
    "event_attendee",
    Base.metadata,
    Column("event_id", String, ForeignKey("event.id", ondelete="CASCADE"), primary_key=True),
    Column("attendee_id", String, ForeignKey("attendee.id", ondelete="CASCADE"), primary_key=True),
    Column("checked_in", Boolean, default=False),
    Column("checked_in_at", DateTime, nullable=True),
)


class Attendee(Base):
    """
    Database model for attendees
    """
    __tablename__ = 'attendee'

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=True)  # Can be null for guest attendees
    email = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    is_guest = Column(Boolean, default=False)  # True if not linked to a registered user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="attendee_profiles")
    tickets = relationship("Ticket", back_populates="attendee")
    events = relationship(
        "Event",
        secondary=event_attendee,
        backref="attendees"
    )

    def __repr__(self):
        return f"<Attendee {self.first_name} {self.last_name}>" 