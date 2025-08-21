"""
Waitlist Management Schemas
Pydantic models for waitlist API requests and responses
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.schemas.user import UserBase


class WaitlistStatusEnum(str, Enum):
    """Status of waitlist entries"""
    ACTIVE = "active"
    NOTIFIED = "notified"
    CONVERTED = "converted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WaitlistPriorityEnum(str, Enum):
    """Priority levels for waitlist entries"""
    NORMAL = "normal"
    HIGH = "high"
    VIP = "vip"
    STAFF = "staff"


class NotificationTypeEnum(str, Enum):
    """Types of notifications"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


# Event Waitlist Schemas

class EventWaitlistBase(BaseModel):
    """Base schema for event waitlists"""
    is_enabled: bool = True
    max_capacity: Optional[int] = Field(default=None, ge=1, le=10000)
    auto_notify: bool = True
    notification_window_hours: int = Field(default=24, ge=1, le=168)  # Max 1 week
    enable_priority_queue: bool = False
    vip_percentage: float = Field(default=0.1, ge=0.0, le=1.0)
    custom_message: Optional[str] = Field(default=None, max_length=1000)

    @validator('notification_window_hours')
    def validate_notification_window(cls, v):
        if v < 1 or v > 168:  # 1 hour to 1 week
            raise ValueError('Notification window must be between 1 and 168 hours')
        return v


class EventWaitlistCreate(EventWaitlistBase):
    """Schema for creating event waitlists"""
    event_id: str


class EventWaitlistUpdate(BaseModel):
    """Schema for updating event waitlists"""
    is_enabled: Optional[bool] = None
    max_capacity: Optional[int] = Field(default=None, ge=1, le=10000)
    auto_notify: Optional[bool] = None
    notification_window_hours: Optional[int] = Field(default=None, ge=1, le=168)
    enable_priority_queue: Optional[bool] = None
    vip_percentage: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    custom_message: Optional[str] = Field(default=None, max_length=1000)


class EventWaitlist(EventWaitlistBase):
    """Schema for event waitlist responses"""
    id: int
    uuid: str
    event_id: str
    total_entries: int
    active_entries: int
    converted_entries: int
    conversion_rate: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Waitlist Entry Schemas

class WaitlistEntryBase(BaseModel):
    """Base schema for waitlist entries"""
    requested_tickets: int = Field(default=1, ge=1, le=10)
    max_price: Optional[float] = Field(default=None, ge=0)
    preferred_ticket_types: Optional[List[str]] = None
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    source: Optional[str] = Field(default=None, max_length=50)

    @validator('preferred_ticket_types')
    def validate_ticket_types(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError('Preferred ticket types cannot be empty if provided')
        return v


class WaitlistEntryCreate(WaitlistEntryBase):
    """Schema for joining a waitlist"""
    event_id: str


class WaitlistEntryUpdate(BaseModel):
    """Schema for updating waitlist entries"""
    requested_tickets: Optional[int] = Field(default=None, ge=1, le=10)
    max_price: Optional[float] = Field(default=None, ge=0)
    preferred_ticket_types: Optional[List[str]] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


class WaitlistEntry(WaitlistEntryBase):
    """Schema for waitlist entry responses"""
    id: int
    uuid: str
    waitlist_id: int
    user_id: str
    event_id: str
    position: int
    priority: WaitlistPriorityEnum
    priority_score: float
    status: WaitlistStatusEnum
    joined_at: datetime
    notified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WaitlistEntryWithUser(WaitlistEntry):
    """Waitlist entry with user information"""
    user: UserBase

    class Config:
        from_attributes = True


# Waitlist Notification Schemas

class WaitlistNotificationBase(BaseModel):
    """Base schema for waitlist notifications"""
    notification_type: NotificationTypeEnum
    subject: Optional[str] = Field(default=None, max_length=255)
    message: str = Field(..., min_length=1, max_length=5000)
    available_tickets: int = Field(..., ge=1)
    ticket_types: Optional[List[str]] = None
    special_offer: Optional[Dict[str, Any]] = None


class WaitlistNotificationCreate(WaitlistNotificationBase):
    """Schema for creating waitlist notifications"""
    entry_id: int
    expires_at: datetime

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('Expiration time must be in the future')
        return v


class WaitlistNotification(WaitlistNotificationBase):
    """Schema for waitlist notification responses"""
    id: int
    uuid: str
    waitlist_id: int
    entry_id: int
    user_id: str
    sent_at: datetime
    expires_at: datetime
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    response_action: Optional[str] = None
    delivery_status: str
    delivery_attempts: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Waitlist Release Schemas

class WaitlistReleaseBase(BaseModel):
    """Base schema for waitlist releases"""
    tickets_released: int = Field(..., ge=1)
    ticket_type_id: Optional[str] = None
    release_reason: str = Field(..., min_length=1, max_length=255)
    processing_method: str = Field(default="fifo", pattern=r'^(fifo|priority|random)$')
    notes: Optional[str] = Field(default=None, max_length=1000)


class WaitlistReleaseCreate(WaitlistReleaseBase):
    """Schema for creating waitlist releases"""
    event_id: str


class WaitlistRelease(WaitlistReleaseBase):
    """Schema for waitlist release responses"""
    id: int
    uuid: str
    event_id: str
    waitlist_id: int
    processed_at: datetime
    notifications_sent: int
    successful_conversions: int
    failed_notifications: int
    vip_notifications: int
    regular_notifications: int
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Waitlist Preferences Schemas

class WaitlistPreferencesBase(BaseModel):
    """Base schema for waitlist preferences"""
    default_email_notifications: bool = True
    default_sms_notifications: bool = False
    default_push_notifications: bool = True
    preferred_notification_window: int = Field(default=24, ge=1, le=168)
    auto_purchase_enabled: bool = False
    auto_purchase_max_price: Optional[float] = Field(default=None, ge=0)
    preferred_notification_time_start: int = Field(default=9, ge=0, le=23)
    preferred_notification_time_end: int = Field(default=21, ge=0, le=23)
    timezone: str = Field(default="UTC", max_length=50)

    @validator('preferred_notification_time_end')
    def validate_notification_times(cls, v, values):
        start_time = values.get('preferred_notification_time_start', 9)
        if v <= start_time:
            raise ValueError('End time must be after start time')
        return v


class WaitlistPreferencesUpdate(WaitlistPreferencesBase):
    """Schema for updating waitlist preferences"""
    pass


class WaitlistPreferences(WaitlistPreferencesBase):
    """Schema for waitlist preferences responses"""
    id: int
    user_id: str
    priority_eligible: bool
    priority_level: WaitlistPriorityEnum
    priority_expires_at: Optional[datetime] = None
    total_waitlist_joins: int
    successful_conversions: int
    average_wait_time_hours: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Utility and Response Schemas

class WaitlistStats(BaseModel):
    """Schema for waitlist statistics"""
    event_id: str
    waitlist_enabled: bool
    total_entries: int
    active_entries: int
    average_position: float
    estimated_wait_time_hours: float
    conversion_rate: float
    latest_activity: Optional[datetime] = None


class WaitlistPosition(BaseModel):
    """Schema for user's waitlist position"""
    entry_id: int
    position: int
    effective_position: int
    estimated_wait_time_hours: float
    ahead_of_user: int
    total_in_waitlist: int
    priority: WaitlistPriorityEnum
    status: WaitlistStatusEnum
    joined_at: datetime


class BulkWaitlistOperation(BaseModel):
    """Schema for bulk waitlist operations"""
    entry_ids: List[int]
    operation: str = Field(..., pattern=r'^(notify|cancel|promote|demote)$')
    reason: Optional[str] = Field(default=None, max_length=500)
    notification_message: Optional[str] = Field(default=None, max_length=1000)


class BulkWaitlistResult(BaseModel):
    """Schema for bulk operation results"""
    operation: str
    total_requested: int
    successful: int
    failed: int
    errors: List[str] = []
    processed_entry_ids: List[int] = []


class WaitlistAnalytics(BaseModel):
    """Schema for waitlist analytics"""
    event_id: str
    total_entries: int
    active_entries: int
    converted_entries: int
    conversion_rate: float
    average_wait_time_hours: float
    priority_distribution: Dict[str, int]
    hourly_join_rate: List[Dict[str, Any]]
    conversion_by_position: List[Dict[str, Any]]
    notification_response_rates: Dict[str, float]


class WaitlistEventSummary(BaseModel):
    """Schema for event waitlist summary"""
    event_id: str
    event_title: str
    waitlist_enabled: bool
    capacity_remaining: int
    waitlist_count: int
    conversion_rate: float
    estimated_availability: Optional[datetime] = None