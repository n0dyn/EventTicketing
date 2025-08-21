from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, Field, ConfigDict


# Shared properties
class OrganizationBase(BaseModel):
    """
    Base Organization schema with shared properties
    """
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = True


# Properties to receive via API on creation
class OrganizationCreate(OrganizationBase):
    """
    Organization creation schema
    """
    name: str
    slug: str


# Properties to receive via API on update
class OrganizationUpdate(OrganizationBase):
    """
    Organization update schema
    """
    pass


# Properties shared by models stored in DB
class OrganizationInDBBase(OrganizationBase):
    """
    Base schema for Organization in DB
    """
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Additional properties to return via API
class Organization(OrganizationInDBBase):
    """
    Organization schema for response
    """
    pass


# For listing members/users
class OrganizationMember(BaseModel):
    """
    Organization member schema
    """
    user_id: str
    role: str
    
    model_config = ConfigDict(from_attributes=True) 