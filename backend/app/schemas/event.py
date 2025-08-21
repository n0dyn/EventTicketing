from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field, ConfigDict

from app.models.event import EventStatus


# Shared properties
class EventBase(BaseModel):
    """
    Base Event schema with shared properties
    """
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = "UTC"
    featured_image: Optional[str] = None
    banner_image: Optional[str] = None
    capacity: Optional[int] = None
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    is_free: Optional[bool] = False
    status: Optional[EventStatus] = EventStatus.DRAFT
    is_public: Optional[bool] = True
    organization_id: Optional[str] = None


# Properties to receive via API on creation
class EventCreate(EventBase):
    """
    Event creation schema
    """
    title: str
    slug: str
    start_time: datetime
    end_time: datetime
    organization_id: str
    category_ids: Optional[List[str]] = []


# Properties to receive via API on update
class EventUpdate(EventBase):
    """
    Event update schema
    """
    category_ids: Optional[List[str]] = None


# Properties shared by models stored in DB
class EventInDBBase(EventBase):
    """
    Base schema for Event in DB
    """
    id: str
    title: str
    slug: str
    owner_id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Additional properties to return via API
class Event(EventInDBBase):
    """
    Event schema for response
    """
    categories: list = []
    owner: Optional[dict] = None
    organization: Optional[dict] = None


# Alias for API responses
EventResponse = Event 