"""
Waitlist Management Models
Handles event waitlists, priority queuing, and automatic notifications
"""

from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Float
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base_class import Base


class WaitlistStatus(PyEnum):
    """Status of waitlist entries"""
    ACTIVE = "active"
    NOTIFIED = "notified"  # User has been notified of availability
    CONVERTED = "converted"  # User purchased ticket
    EXPIRED = "expired"  # Notification expired
    CANCELLED = "cancelled"  # User cancelled waitlist entry


class WaitlistPriority(PyEnum):
    """Priority levels for waitlist entries"""
    NORMAL = "normal"
    HIGH = "high"
    VIP = "vip"
    STAFF = "staff"


class EventWaitlist(Base):
    """
    Represents a waitlist for a specific event
    Manages overall waitlist settings and statistics
    """
    __tablename__ = "event_waitlists"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Event association
    event_id = Column(String, ForeignKey("events.id"), nullable=False, unique=True)
    
    # Waitlist settings
    is_enabled = Column(Boolean, default=True)
    max_capacity = Column(Integer, nullable=True)  # Max waitlist size
    auto_notify = Column(Boolean, default=True)  # Auto-notify when tickets available
    notification_window_hours = Column(Integer, default=24)  # How long users have to respond
    
    # Priority settings
    enable_priority_queue = Column(Boolean, default=False)
    vip_percentage = Column(Float, default=0.1)  # % of releases for VIP users
    
    # Notification settings
    notification_template_id = Column(String, nullable=True)
    custom_message = Column(Text, nullable=True)
    
    # Statistics (updated via triggers or background jobs)
    total_entries = Column(Integer, default=0)
    active_entries = Column(Integer, default=0)
    converted_entries = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", back_populates="waitlist")
    entries = relationship("WaitlistEntry", back_populates="waitlist", cascade="all, delete-orphan")
    notifications = relationship("WaitlistNotification", back_populates="waitlist", cascade="all, delete-orphan")
    
    @hybrid_property
    def current_position_count(self):
        """Get current number of active waitlist entries"""
        return len([e for e in self.entries if e.status == WaitlistStatus.ACTIVE.value])
    
    @hybrid_property
    def is_full(self):
        """Check if waitlist has reached capacity"""
        if not self.max_capacity:
            return False
        return self.current_position_count >= self.max_capacity
    
    def get_next_position(self) -> int:
        """Get the next position number for new entries"""
        if not self.entries:
            return 1
        
        active_entries = [e for e in self.entries if e.status == WaitlistStatus.ACTIVE.value]
        if not active_entries:
            return 1
        
        return max(e.position for e in active_entries) + 1


class WaitlistEntry(Base):
    """
    Individual waitlist entry for a user
    Tracks position, priority, and notification history
    """
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # References
    waitlist_id = Column(Integer, ForeignKey("event_waitlists.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)  # Denormalized for queries
    
    # Position and priority
    position = Column(Integer, nullable=False, index=True)
    priority = Column(String, default=WaitlistPriority.NORMAL.value, index=True)
    priority_score = Column(Float, default=0.0)  # Custom priority scoring
    
    # Status and timing
    status = Column(String, default=WaitlistStatus.ACTIVE.value, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow, index=True)
    notified_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    converted_at = Column(DateTime, nullable=True)
    
    # User preferences
    requested_tickets = Column(Integer, default=1)
    max_price = Column(Float, nullable=True)  # Maximum price willing to pay
    preferred_ticket_types = Column(JSON, nullable=True)  # List of preferred ticket type IDs
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    
    # Additional data
    source = Column(String, nullable=True)  # How they joined (web, mobile, admin)
    metadata = Column(JSONB, nullable=True)  # Additional custom data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    waitlist = relationship("EventWaitlist", back_populates="entries")
    user = relationship("User", back_populates="waitlist_entries")
    event = relationship("Event")
    notifications = relationship("WaitlistNotification", back_populates="entry", cascade="all, delete-orphan")
    
    @hybrid_property
    def is_active(self):
        """Check if entry is still active"""
        return self.status == WaitlistStatus.ACTIVE.value
    
    @hybrid_property
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @hybrid_property
    def time_on_waitlist(self):
        """Get time spent on waitlist"""
        end_time = self.converted_at or self.notified_at or datetime.utcnow()
        return end_time - self.joined_at
    
    def calculate_effective_position(self) -> int:
        """Calculate position considering priority"""
        if self.priority == WaitlistPriority.STAFF.value:
            return 0  # Staff always first
        elif self.priority == WaitlistPriority.VIP.value:
            return self.position * 0.5  # VIP gets 50% boost
        elif self.priority == WaitlistPriority.HIGH.value:
            return self.position * 0.8  # High priority gets 20% boost
        else:
            return self.position


class WaitlistNotification(Base):
    """
    Tracks notifications sent to waitlist users
    Handles notification delivery and response tracking
    """
    __tablename__ = "waitlist_notifications"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # References
    waitlist_id = Column(Integer, ForeignKey("event_waitlists.id"), nullable=False)
    entry_id = Column(Integer, ForeignKey("waitlist_entries.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Notification details
    notification_type = Column(String, nullable=False)  # email, sms, push, etc.
    subject = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    
    # Tickets available
    available_tickets = Column(Integer, nullable=False)
    ticket_types = Column(JSON, nullable=True)  # Available ticket types
    special_offer = Column(JSONB, nullable=True)  # Special pricing or conditions
    
    # Timing
    sent_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Response tracking
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    response_action = Column(String, nullable=True)  # purchased, declined, expired
    
    # Delivery status
    delivery_status = Column(String, default="sent")  # sent, delivered, failed, bounced
    delivery_attempts = Column(Integer, default=1)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    waitlist = relationship("EventWaitlist", back_populates="notifications")
    entry = relationship("WaitlistEntry", back_populates="notifications")
    user = relationship("User")
    
    @hybrid_property
    def is_expired(self):
        """Check if notification has expired"""
        return datetime.utcnow() > self.expires_at
    
    @hybrid_property
    def response_time(self):
        """Get time taken to respond"""
        if not self.responded_at:
            return None
        return self.responded_at - self.sent_at


class WaitlistRelease(Base):
    """
    Tracks ticket releases and waitlist processing
    Records when tickets become available and how they're distributed
    """
    __tablename__ = "waitlist_releases"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Event and tickets
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    waitlist_id = Column(Integer, ForeignKey("event_waitlists.id"), nullable=False)
    
    # Release details
    tickets_released = Column(Integer, nullable=False)
    ticket_type_id = Column(String, nullable=True)  # Specific ticket type or null for any
    release_reason = Column(String, nullable=False)  # cancellation, new_inventory, etc.
    
    # Processing details
    processed_at = Column(DateTime, default=datetime.utcnow)
    processing_method = Column(String, default="fifo")  # fifo, priority, random
    
    # Results
    notifications_sent = Column(Integer, default=0)
    successful_conversions = Column(Integer, default=0)
    failed_notifications = Column(Integer, default=0)
    
    # Priority distribution
    vip_notifications = Column(Integer, default=0)
    regular_notifications = Column(Integer, default=0)
    
    # Metadata
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)  # Admin user who triggered release
    metadata = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event")
    waitlist = relationship("EventWaitlist")
    
    @hybrid_property
    def conversion_rate(self):
        """Calculate conversion rate for this release"""
        if self.notifications_sent == 0:
            return 0.0
        return (self.successful_conversions / self.notifications_sent) * 100


class WaitlistPreference(Base):
    """
    User-specific waitlist preferences and settings
    Allows users to customize their waitlist experience
    """
    __tablename__ = "waitlist_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Global notification preferences
    default_email_notifications = Column(Boolean, default=True)
    default_sms_notifications = Column(Boolean, default=False)
    default_push_notifications = Column(Boolean, default=True)
    
    # Response time preferences
    preferred_notification_window = Column(Integer, default=24)  # Hours
    auto_purchase_enabled = Column(Boolean, default=False)  # Auto-purchase when notified
    auto_purchase_max_price = Column(Float, nullable=True)
    
    # Priority settings (for eligible users)
    priority_eligible = Column(Boolean, default=False)
    priority_level = Column(String, default=WaitlistPriority.NORMAL.value)
    priority_expires_at = Column(DateTime, nullable=True)
    
    # Communication preferences
    preferred_notification_time_start = Column(Integer, default=9)  # 9 AM
    preferred_notification_time_end = Column(Integer, default=21)   # 9 PM
    timezone = Column(String, default="UTC")
    
    # Statistics
    total_waitlist_joins = Column(Integer, default=0)
    successful_conversions = Column(Integer, default=0)
    average_wait_time_hours = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="waitlist_preferences")
    
    @hybrid_property
    def conversion_rate(self):
        """Calculate user's historical conversion rate"""
        if self.total_waitlist_joins == 0:
            return 0.0
        return (self.successful_conversions / self.total_waitlist_joins) * 100