from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Shared properties
class UserBase(BaseModel):
    """
    Base User schema with shared properties
    """
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    """
    User creation schema
    """
    email: EmailStr
    password: str


# Properties to receive via API on update
class UserUpdate(UserBase):
    """
    User update schema
    """
    password: Optional[str] = None


# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    """
    Base schema for User in DB
    """
    id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Additional properties to return via API
class User(UserInDBBase):
    """
    User schema for response
    """
    pass


# Additional properties stored in DB
class UserInDB(UserInDBBase):
    """
    User schema with password hash
    """
    hashed_password: str


# Alias for API responses
UserResponse = User 