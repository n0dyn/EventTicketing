from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


# Shared properties
class EventCategoryBase(BaseModel):
    """
    Base EventCategory schema with shared properties
    """
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


# Properties to receive via API on creation
class EventCategoryCreate(EventCategoryBase):
    """
    EventCategory creation schema
    """
    name: str
    slug: str


# Properties to receive via API on update
class EventCategoryUpdate(EventCategoryBase):
    """
    EventCategory update schema
    """
    pass


# Properties shared by models stored in DB
class EventCategoryInDBBase(EventCategoryBase):
    """
    Base schema for EventCategory in DB
    """
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Additional properties to return via API
class EventCategory(EventCategoryInDBBase):
    """
    EventCategory schema for response
    """
    pass 