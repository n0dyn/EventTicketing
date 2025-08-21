"""
Recurring Events Schemas
Pydantic models for recurring event API requests and responses
"""

from datetime import date, time, datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.schemas.event import EventBase


class RecurrenceTypeEnum(str, Enum):
    """Types of recurrence patterns"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


# Recurrence Pattern Schemas
class RecurrencePatternBase(BaseModel):
    """Base schema for recurrence patterns"""
    recurrence_type: RecurrenceTypeEnum
    interval_count: int = Field(default=1, ge=1, le=365)
    
    # Weekly recurrence
    weekdays: Optional[List[int]] = Field(default=None, description="Days of week (0=Monday, 6=Sunday)")
    
    # Monthly recurrence
    month_day: Optional[int] = Field(default=None, ge=1, le=31)
    month_week: Optional[int] = Field(default=None, ge=-1, le=4, description="Week of month (-1=last)")
    month_weekday: Optional[int] = Field(default=None, ge=0, le=6)
    
    # Yearly recurrence
    year_month: Optional[int] = Field(default=None, ge=1, le=12)
    year_day: Optional[int] = Field(default=None, ge=1, le=31)
    
    # End conditions
    end_date: Optional[date] = None
    occurrence_count: Optional[int] = Field(default=None, ge=1, le=1000)
    
    # Advanced options
    exclude_dates: Optional[List[str]] = Field(default=None, description="ISO date strings to exclude")
    include_dates: Optional[List[str]] = Field(default=None, description="Additional ISO date strings")
    timezone: str = Field(default="UTC")
    
    # Custom rule
    custom_rule: Optional[str] = Field(default=None, description="RRULE or custom expression")

    @validator('weekdays')
    def validate_weekdays(cls, v):
        if v is not None:
            if not all(0 <= day <= 6 for day in v):
                raise ValueError('Weekdays must be between 0 (Monday) and 6 (Sunday)')
            if len(v) == 0:
                raise ValueError('Weekdays cannot be empty if provided')
        return v

    @validator('exclude_dates', 'include_dates')
    def validate_date_strings(cls, v):
        if v is not None:
            for date_str in v:
                try:
                    datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError(f'Invalid date format: {date_str}. Use ISO format (YYYY-MM-DD)')
        return v


class RecurrencePatternCreate(RecurrencePatternBase):
    """Schema for creating recurrence patterns"""
    pass


class RecurrencePatternUpdate(BaseModel):
    """Schema for updating recurrence patterns"""
    recurrence_type: Optional[RecurrenceTypeEnum] = None
    interval_count: Optional[int] = Field(default=None, ge=1, le=365)
    weekdays: Optional[List[int]] = None
    month_day: Optional[int] = Field(default=None, ge=1, le=31)
    month_week: Optional[int] = Field(default=None, ge=-1, le=4)
    month_weekday: Optional[int] = Field(default=None, ge=0, le=6)
    year_month: Optional[int] = Field(default=None, ge=1, le=12)
    year_day: Optional[int] = Field(default=None, ge=1, le=31)
    end_date: Optional[date] = None
    occurrence_count: Optional[int] = Field(default=None, ge=1, le=1000)
    exclude_dates: Optional[List[str]] = None
    include_dates: Optional[List[str]] = None
    timezone: Optional[str] = None
    custom_rule: Optional[str] = None


class RecurrencePattern(RecurrencePatternBase):
    """Schema for recurrence pattern responses"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Event Series Schemas
class EventSeriesBase(BaseModel):
    """Base schema for event series"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Template data for events
    template_data: Optional[Dict[str, Any]] = None
    
    # Series dates
    series_start_date: date
    series_end_date: Optional[date] = None
    
    # Time settings
    default_start_time: Optional[time] = None
    default_end_time: Optional[time] = None
    default_duration_minutes: Optional[int] = Field(default=None, ge=1, le=10080)  # Max 1 week
    
    # Series settings
    is_active: bool = True
    auto_publish: bool = False
    advance_days: int = Field(default=30, ge=1, le=365)
    max_instances: int = Field(default=100, ge=1, le=1000)
    
    @validator('series_end_date')
    def validate_end_date(cls, v, values):
        if v is not None and 'series_start_date' in values:
            if v <= values['series_start_date']:
                raise ValueError('End date must be after start date')
        return v

    @validator('default_end_time')
    def validate_end_time(cls, v, values):
        if v is not None and 'default_start_time' in values and values['default_start_time'] is not None:
            if v <= values['default_start_time']:
                raise ValueError('End time must be after start time')
        return v


class EventSeriesCreate(EventSeriesBase):
    """Schema for creating event series"""
    recurrence_pattern: RecurrencePatternCreate
    organization_id: Optional[str] = None


class EventSeriesUpdate(BaseModel):
    """Schema for updating event series"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    series_end_date: Optional[date] = None
    default_start_time: Optional[time] = None
    default_end_time: Optional[time] = None
    default_duration_minutes: Optional[int] = Field(default=None, ge=1, le=10080)
    is_active: Optional[bool] = None
    auto_publish: Optional[bool] = None
    advance_days: Optional[int] = Field(default=None, ge=1, le=365)
    max_instances: Optional[int] = Field(default=None, ge=1, le=1000)
    recurrence_pattern: Optional[RecurrencePatternUpdate] = None


class EventSeries(EventSeriesBase):
    """Schema for event series responses"""
    id: int
    uuid: str
    owner_id: str
    organization_id: Optional[str] = None
    total_events: int
    upcoming_events: int
    recurrence_pattern: RecurrencePattern
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Event Instance Schemas
class EventInstanceBase(BaseModel):
    """Base schema for event instances"""
    custom_title: Optional[str] = Field(default=None, max_length=255)
    custom_description: Optional[str] = None
    custom_location: Optional[str] = Field(default=None, max_length=255)
    custom_start_time: Optional[datetime] = None
    custom_end_time: Optional[datetime] = None
    is_cancelled: bool = False
    cancellation_reason: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None

    @validator('custom_end_time')
    def validate_custom_end_time(cls, v, values):
        if v is not None and 'custom_start_time' in values and values['custom_start_time'] is not None:
            if v <= values['custom_start_time']:
                raise ValueError('Custom end time must be after custom start time')
        return v


class EventInstanceCreate(EventInstanceBase):
    """Schema for creating event instances"""
    event_id: str
    event_series_id: int


class EventInstanceUpdate(EventInstanceBase):
    """Schema for updating event instances"""
    pass


class EventInstance(EventInstanceBase):
    """Schema for event instance responses"""
    id: int
    event_id: str
    event_series_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Utility Schemas
class RecurrencePreview(BaseModel):
    """Schema for previewing recurrence dates"""
    dates: List[date]
    total_count: int
    preview_count: int
    has_more: bool


class EventSeriesPreview(BaseModel):
    """Schema for previewing event series generation"""
    series_info: EventSeries
    preview_dates: List[date]
    existing_events_count: int
    new_events_count: int
    total_preview_count: int


class BulkEventOperation(BaseModel):
    """Schema for bulk operations on event series"""
    event_ids: List[str]
    operation: str = Field(..., pattern=r'^(publish|unpublish|cancel|delete)$')
    reason: Optional[str] = None


class BulkEventResult(BaseModel):
    """Schema for bulk operation results"""
    operation: str
    total_requested: int
    successful: int
    failed: int
    errors: List[str] = []
    processed_event_ids: List[str] = []


# Extended Event Schema with Series Info
class EventWithSeries(EventBase):
    """Event schema including series information"""
    is_part_of_series: bool
    event_series_id: Optional[int] = None
    event_series: Optional[EventSeries] = None
    event_instance: Optional[EventInstance] = None
    
    class Config:
        from_attributes = True