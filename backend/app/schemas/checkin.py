"""
Check-in System Schemas
Pydantic models for QR code check-in API requests and responses
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.schemas.user import UserBase


class CheckInStatusEnum(str, Enum):
    """Status of check-in attempts"""
    PENDING = "pending"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    INVALID = "invalid"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"


class AccessLevelEnum(str, Enum):
    """Access levels for different areas"""
    GENERAL = "general"
    VIP = "vip"
    BACKSTAGE = "backstage"
    STAFF = "staff"
    PRESS = "press"


class ScanResultEnum(str, Enum):
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


# Ticket QR Code Schemas

class TicketQRCodeBase(BaseModel):
    """Base schema for ticket QR codes"""
    access_level: AccessLevelEnum = AccessLevelEnum.GENERAL
    restricted_areas: Optional[List[str]] = None
    usage_limit: int = Field(default=1, ge=1, le=10)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    @validator('valid_until')
    def validate_valid_until(cls, v, values):
        if v is not None and 'valid_from' in values and values['valid_from'] is not None:
            if v <= values['valid_from']:
                raise ValueError('Valid until must be after valid from')
        return v


class TicketQRCodeCreate(TicketQRCodeBase):
    """Schema for creating ticket QR codes"""
    ticket_id: str
    order_id: str
    event_id: str


class TicketQRCode(TicketQRCodeBase):
    """Schema for ticket QR code responses"""
    id: int
    uuid: str
    ticket_id: str
    order_id: str
    event_id: str
    qr_code_data: str
    is_active: bool
    current_usage: int
    generated_at: datetime
    version: int

    class Config:
        from_attributes = True


# Attendee Check-in Schemas

class AttendeeCheckInBase(BaseModel):
    """Base schema for attendee check-ins"""
    check_in_location: Optional[str] = Field(default=None, max_length=255)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    accuracy: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=1000)


class ScanRequest(BaseModel):
    """Schema for QR code scan requests"""
    qr_code_data: str = Field(..., min_length=1)
    scanner_device_id: str = Field(..., min_length=1, max_length=255)
    check_in_location: Optional[str] = Field(default=None, max_length=255)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    accuracy: Optional[float] = Field(default=None, ge=0)
    force_check_in: bool = Field(default=False)  # Override some validations


class ScanResponse(BaseModel):
    """Schema for QR code scan responses"""
    success: bool
    result: ScanResultEnum
    message: str
    check_in_id: Optional[int] = None
    attendee_info: Optional[Dict[str, Any]] = None
    event_info: Optional[Dict[str, Any]] = None
    warnings: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AttendeeCheckIn(AttendeeCheckInBase):
    """Schema for attendee check-in responses"""
    id: int
    uuid: str
    qr_code_id: int
    ticket_id: str
    event_id: str
    user_id: str
    status: CheckInStatusEnum
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    scanner_device_id: Optional[str] = None
    scanner_user_id: Optional[str] = None
    scan_result: ScanResultEnum
    validation_errors: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AttendeeCheckInWithUser(AttendeeCheckIn):
    """Attendee check-in with user information"""
    user: UserBase
    scanner_user: Optional[UserBase] = None

    class Config:
        from_attributes = True


# Check-in Location Schemas

class CheckInLocationBase(BaseModel):
    """Base schema for check-in locations"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    location_type: str = Field(default="entrance", pattern=r'^(entrance|exit|checkpoint)$')
    required_access_level: AccessLevelEnum = AccessLevelEnum.GENERAL
    allowed_ticket_types: Optional[List[str]] = None
    max_capacity: Optional[int] = Field(default=None, ge=1)
    opens_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    geofence_radius: float = Field(default=50.0, ge=1.0, le=1000.0)
    settings: Optional[Dict[str, Any]] = None

    @validator('closes_at')
    def validate_closes_at(cls, v, values):
        if v is not None and 'opens_at' in values and values['opens_at'] is not None:
            if v <= values['opens_at']:
                raise ValueError('Closes at must be after opens at')
        return v


class CheckInLocationCreate(CheckInLocationBase):
    """Schema for creating check-in locations"""
    event_id: str


class CheckInLocationUpdate(BaseModel):
    """Schema for updating check-in locations"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    location_type: Optional[str] = Field(default=None, pattern=r'^(entrance|exit|checkpoint)$')
    required_access_level: Optional[AccessLevelEnum] = None
    allowed_ticket_types: Optional[List[str]] = None
    max_capacity: Optional[int] = Field(default=None, ge=1)
    opens_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    geofence_radius: Optional[float] = Field(default=None, ge=1.0, le=1000.0)
    settings: Optional[Dict[str, Any]] = None


class CheckInLocation(CheckInLocationBase):
    """Schema for check-in location responses"""
    id: int
    uuid: str
    event_id: str
    current_occupancy: int
    is_active: bool
    is_monitored: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Scan Session Schemas

class ScanSessionBase(BaseModel):
    """Base schema for scan sessions"""
    device_id: str = Field(..., min_length=1, max_length=255)
    device_name: Optional[str] = Field(default=None, max_length=255)
    device_info: Optional[Dict[str, Any]] = None


class ScanSessionCreate(ScanSessionBase):
    """Schema for creating scan sessions"""
    event_id: str
    location_id: Optional[int] = None


class ScanSessionStart(BaseModel):
    """Schema for starting scan sessions"""
    event_id: str
    location_id: Optional[int] = None
    device_id: str = Field(..., min_length=1, max_length=255)
    device_name: Optional[str] = Field(default=None, max_length=255)
    device_info: Optional[Dict[str, Any]] = None


class ScanSession(ScanSessionBase):
    """Schema for scan session responses"""
    id: int
    uuid: str
    session_token: str
    user_id: str
    event_id: str
    location_id: Optional[int] = None
    is_active: bool
    started_at: datetime
    last_activity: datetime
    ended_at: Optional[datetime] = None
    scans_performed: int
    successful_scans: int
    failed_scans: int
    ip_address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Statistics and Analytics Schemas

class CheckInStats(BaseModel):
    """Schema for check-in statistics"""
    event_id: str
    total_tickets: int
    checked_in_count: int
    checked_out_count: int
    currently_at_event: int
    peak_occupancy: int
    peak_occupancy_time: Optional[datetime] = None
    average_check_in_time: float
    busiest_entrance: Optional[str] = None
    busiest_hour: Optional[int] = None
    no_show_count: int
    late_arrival_count: int
    attendance_rate: float
    current_occupancy_rate: float
    hourly_check_ins: Optional[Dict[str, int]] = None
    location_breakdown: Optional[Dict[str, int]] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class RealTimeCheckInData(BaseModel):
    """Schema for real-time check-in data"""
    event_id: str
    current_attendees: int
    total_capacity: int
    check_ins_last_hour: int
    check_ins_last_15_min: int
    peak_time_today: Optional[str] = None
    busiest_location: Optional[str] = None
    current_locations: List[Dict[str, Any]] = []
    recent_check_ins: List[Dict[str, Any]] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CheckInAnalytics(BaseModel):
    """Schema for check-in analytics"""
    event_id: str
    date_range: Dict[str, datetime]
    total_scans: int
    successful_scans: int
    failed_scans: int
    success_rate: float
    unique_attendees: int
    repeat_scan_rate: float
    average_dwell_time_minutes: float
    peak_periods: List[Dict[str, Any]]
    location_performance: List[Dict[str, Any]]
    scan_patterns: Dict[str, Any]
    recommendations: List[str]


# Utility and Response Schemas

class QRCodeValidation(BaseModel):
    """Schema for QR code validation"""
    is_valid: bool
    ticket_id: Optional[str] = None
    event_id: Optional[str] = None
    access_level: Optional[AccessLevelEnum] = None
    usage_remaining: Optional[int] = None
    valid_until: Optional[datetime] = None
    errors: List[str] = []


class BulkCheckInOperation(BaseModel):
    """Schema for bulk check-in operations"""
    qr_codes: List[str] = Field(..., min_items=1, max_items=100)
    scanner_device_id: str = Field(..., min_length=1, max_length=255)
    check_in_location: Optional[str] = Field(default=None, max_length=255)
    force_check_in: bool = Field(default=False)
    notes: Optional[str] = Field(default=None, max_length=500)


class BulkCheckInResult(BaseModel):
    """Schema for bulk check-in results"""
    total_processed: int
    successful: int
    failed: int
    results: List[ScanResponse]
    summary: Dict[str, int]  # Count by result type
    processing_time_seconds: float


class AttendeeSearchResult(BaseModel):
    """Schema for attendee search results"""
    ticket_id: str
    user_name: str
    user_email: str
    ticket_type: str
    check_in_status: CheckInStatusEnum
    check_in_time: Optional[datetime] = None
    qr_code_data: str
    access_level: AccessLevelEnum


class CheckInExport(BaseModel):
    """Schema for check-in data export"""
    event_id: str
    export_format: str = Field(..., pattern=r'^(csv|excel|pdf)$')
    date_range: Optional[Dict[str, datetime]] = None
    include_no_shows: bool = True
    include_metadata: bool = False
    group_by: Optional[str] = Field(default=None, pattern=r'^(hour|location|ticket_type)$')