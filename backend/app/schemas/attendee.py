from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class AttendeeBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    is_guest: bool = False


class AttendeeCreate(AttendeeBase):
    user_id: Optional[str] = None


class AttendeeUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None


class AttendeeInDB(AttendeeBase):
    id: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Public schema
class Attendee(AttendeeInDB):
    pass


class AttendeeList(BaseModel):
    attendees: List[Attendee]
    total: int
    page: int
    size: int 