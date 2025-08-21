"""
Check-in System Models
Handles QR code generation, ticket scanning, and attendee check-in tracking
"""

from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Float
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import hashlib
import secrets

from app.db.base_class import Base


class CheckInStatus(PyEnum):
    """Status of check-in attempts"""
    PENDING = "pending"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    INVALID = "invalid"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"


class AccessLevel(PyEnum):
    """Access levels for different areas"""
    GENERAL = "general"
    VIP = "vip"
    BACKSTAGE = "backstage"
    STAFF = "staff"
    PRESS = "press"


class ScanResult(PyEnum):
    """Results of QR code scanning"""
    SUCCESS = "success"
    INVALID_CODE = "invalid_code"
    EXPIRED_TICKET = "expired_ticket"
    ALREADY_USED = "already_used"
    EVENT_NOT_STARTED = "event_not_started"
    EVENT_ENDED = "event_ended"
    WRONG_EVENT = "wrong_event"
    INSUFFICIENT_ACCESS = "insufficient_access"
    SYSTEM_ERROR = "system_error"


class TicketQRCode(Base):
    """
    QR code data for tickets
    Stores secure QR codes and validates them for check-in
    """
    __tablename__ = "ticket_qr_codes"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Ticket association
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, unique=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    
    # QR code data
    qr_code_data = Column(String, nullable=False, unique=True, index=True)
    qr_code_hash = Column(String, nullable=False, unique=True, index=True)
    
    # Security and validation
    secret_key = Column(String, nullable=False)  # For additional validation
    validation_data = Column(JSONB, nullable=True)  # Additional validation info
    
    # Access control
    access_level = Column(String, default=AccessLevel.GENERAL.value)
    restricted_areas = Column(JSON, nullable=True)  # List of accessible areas
    
    # Status and usage
    is_active = Column(Boolean, default=True)
    usage_limit = Column(Integer, default=1)  # How many times can be scanned
    current_usage = Column(Integer, default=0)
    
    # Timing
    valid_from = Column(DateTime, nullable=True)  # When QR becomes valid
    valid_until = Column(DateTime, nullable=True)  # When QR expires
    
    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String, nullable=True)  # User who generated the code
    version = Column(Integer, default=1)  # For QR code format versioning
    
    # Relationships
    ticket = relationship("Ticket", back_populates="qr_code")
    order = relationship("Order")
    event = relationship("Event")
    check_ins = relationship("AttendeeCheckIn", back_populates="qr_code", cascade="all, delete-orphan")
    
    @hybrid_property
    def is_valid(self):
        """Check if QR code is currently valid"""
        now = datetime.utcnow()
        
        if not self.is_active:
            return False
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        if self.current_usage >= self.usage_limit:
            return False
        
        return True
    
    @hybrid_property
    def can_be_used(self):
        """Check if QR code can still be used"""
        return self.is_valid and self.current_usage < self.usage_limit
    
    def generate_qr_data(self) -> str:
        """Generate secure QR code data"""
        # Create a secure token that includes ticket info and validation data
        timestamp = int(datetime.utcnow().timestamp())
        
        data_components = [
            str(self.ticket_id),
            str(self.event_id),
            str(timestamp),
            self.secret_key[:8]  # First 8 chars of secret for validation
        ]
        
        # Create QR data string
        qr_data = "|".join(data_components)
        
        # Add checksum for integrity
        checksum = hashlib.sha256(f"{qr_data}:{self.secret_key}".encode()).hexdigest()[:8]
        
        return f"{qr_data}|{checksum}"
    
    def validate_qr_data(self, scanned_data: str) -> bool:
        """Validate scanned QR code data"""
        try:
            parts = scanned_data.split("|")
            if len(parts) != 5:  # ticket_id, event_id, timestamp, secret_part, checksum
                return False
            
            ticket_id, event_id, timestamp, secret_part, checksum = parts
            
            # Verify ticket and event match
            if ticket_id != str(self.ticket_id) or event_id != str(self.event_id):
                return False
            
            # Verify secret part
            if secret_part != self.secret_key[:8]:
                return False
            
            # Verify checksum
            qr_data = "|".join(parts[:-1])
            expected_checksum = hashlib.sha256(f"{qr_data}:{self.secret_key}".encode()).hexdigest()[:8]
            
            return checksum == expected_checksum
            
        except Exception:
            return False


class AttendeeCheckIn(Base):
    """
    Records of attendee check-ins and check-outs
    Tracks when and where attendees enter/exit events
    """
    __tablename__ = "attendee_check_ins"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # References
    qr_code_id = Column(Integer, ForeignKey("ticket_qr_codes.id"), nullable=False)
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Check-in details
    status = Column(String, default=CheckInStatus.PENDING.value, index=True)
    check_in_time = Column(DateTime, default=datetime.utcnow, index=True)
    check_out_time = Column(DateTime, nullable=True)
    
    # Location and device info
    check_in_location = Column(String, nullable=True)  # Gate/entrance name
    scanner_device_id = Column(String, nullable=True)  # Device that scanned
    scanner_user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Staff who scanned
    
    # Geolocation (if enabled)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    
    # Additional data
    notes = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)  # Additional scan data
    
    # Validation results
    scan_result = Column(String, default=ScanResult.SUCCESS.value)
    validation_errors = Column(JSON, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    qr_code = relationship("TicketQRCode", back_populates="check_ins")
    ticket = relationship("Ticket")
    event = relationship("Event")
    user = relationship("User", foreign_keys=[user_id])
    scanner_user = relationship("User", foreign_keys=[scanner_user_id])
    
    @hybrid_property
    def duration_at_event(self):
        """Calculate time spent at event"""
        if not self.check_out_time:
            return None
        return self.check_out_time - self.check_in_time
    
    @hybrid_property
    def is_currently_checked_in(self):
        """Check if attendee is currently at the event"""
        return self.status == CheckInStatus.CHECKED_IN.value and not self.check_out_time


class CheckInLocation(Base):
    """
    Defines check-in locations and gates for events
    Allows multiple entry/exit points with different access controls
    """
    __tablename__ = "check_in_locations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Event association
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    
    # Location details
    name = Column(String, nullable=False)  # "Main Entrance", "VIP Gate", etc.
    description = Column(Text, nullable=True)
    location_type = Column(String, default="entrance")  # entrance, exit, checkpoint
    
    # Access control
    required_access_level = Column(String, default=AccessLevel.GENERAL.value)
    allowed_ticket_types = Column(JSON, nullable=True)  # List of allowed ticket type IDs
    
    # Capacity and flow control
    max_capacity = Column(Integer, nullable=True)
    current_occupancy = Column(Integer, default=0)
    
    # Timing
    opens_at = Column(DateTime, nullable=True)
    closes_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_monitored = Column(Boolean, default=True)  # Track occupancy
    
    # Physical location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geofence_radius = Column(Float, default=50.0)  # Meters
    
    # Configuration
    settings = Column(JSONB, nullable=True)  # Additional location settings
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("Event")
    
    @hybrid_property
    def is_open(self):
        """Check if location is currently open"""
        if not self.is_active:
            return False
        
        now = datetime.utcnow()
        
        if self.opens_at and now < self.opens_at:
            return False
        
        if self.closes_at and now > self.closes_at:
            return False
        
        return True
    
    @hybrid_property
    def is_at_capacity(self):
        """Check if location is at capacity"""
        if not self.max_capacity:
            return False
        return self.current_occupancy >= self.max_capacity


class ScanSession(Base):
    """
    Tracks scanning sessions for event staff
    Manages scanner device authentication and session data
    """
    __tablename__ = "scan_sessions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Session details
    session_token = Column(String, nullable=False, unique=True, index=True)
    device_id = Column(String, nullable=False)
    device_name = Column(String, nullable=True)
    
    # User and event
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("check_in_locations.id"), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Statistics
    scans_performed = Column(Integer, default=0)
    successful_scans = Column(Integer, default=0)
    failed_scans = Column(Integer, default=0)
    
    # Device info
    device_info = Column(JSONB, nullable=True)  # Browser, OS, etc.
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    event = relationship("Event")
    location = relationship("CheckInLocation")
    
    @classmethod
    def generate_session_token(cls) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    @hybrid_property
    def success_rate(self):
        """Calculate scan success rate"""
        if self.scans_performed == 0:
            return 0.0
        return (self.successful_scans / self.scans_performed) * 100
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


class CheckInStats(Base):
    """
    Aggregated check-in statistics for events
    Provides real-time analytics for event monitoring
    """
    __tablename__ = "check_in_stats"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("events.id"), nullable=False, unique=True)
    
    # Current status
    total_tickets = Column(Integer, default=0)
    checked_in_count = Column(Integer, default=0)
    checked_out_count = Column(Integer, default=0)
    currently_at_event = Column(Integer, default=0)
    
    # Peak metrics
    peak_occupancy = Column(Integer, default=0)
    peak_occupancy_time = Column(DateTime, nullable=True)
    
    # Flow metrics
    average_check_in_time = Column(Float, default=0.0)  # Seconds
    busiest_entrance = Column(String, nullable=True)
    busiest_hour = Column(Integer, nullable=True)  # Hour of day (0-23)
    
    # Conversion metrics
    no_show_count = Column(Integer, default=0)
    late_arrival_count = Column(Integer, default=0)  # Arrived after event started
    
    # Time-based breakdowns
    hourly_check_ins = Column(JSON, nullable=True)  # Check-ins by hour
    location_breakdown = Column(JSON, nullable=True)  # Check-ins by location
    
    # Last update
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("Event")
    
    @hybrid_property
    def attendance_rate(self):
        """Calculate attendance rate percentage"""
        if self.total_tickets == 0:
            return 0.0
        return (self.checked_in_count / self.total_tickets) * 100
    
    @hybrid_property
    def current_occupancy_rate(self):
        """Calculate current occupancy as percentage of capacity"""
        if self.total_tickets == 0:
            return 0.0
        return (self.currently_at_event / self.total_tickets) * 100