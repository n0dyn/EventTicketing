import uuid
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.attendee import Attendee
from app.schemas.attendee import AttendeeCreate, AttendeeUpdate


def get_attendee(db: Session, attendee_id: str) -> Optional[Attendee]:
    """
    Get attendee by ID
    """
    return db.query(Attendee).filter(Attendee.id == attendee_id).first()


def get_attendee_by_email(db: Session, email: str) -> Optional[Attendee]:
    """
    Get attendee by email
    """
    return db.query(Attendee).filter(Attendee.email == email).first()


def get_attendees(
    db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None
) -> Tuple[List[Attendee], int]:
    """
    Get all attendees with optional search
    """
    query = db.query(Attendee)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Attendee.first_name.ilike(search_term),
                Attendee.last_name.ilike(search_term),
                Attendee.email.ilike(search_term),
                Attendee.company.ilike(search_term),
            )
        )
    
    total = query.count()
    attendees = query.offset(skip).limit(limit).all()
    
    return attendees, total


def get_attendees_by_event(
    db: Session, event_id: str, skip: int = 0, limit: int = 100, search: Optional[str] = None
) -> Tuple[List[Attendee], int]:
    """
    Get attendees for a specific event
    """
    from app.models.attendee import event_attendee
    
    query = db.query(Attendee).join(
        event_attendee, 
        Attendee.id == event_attendee.c.attendee_id
    ).filter(event_attendee.c.event_id == event_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Attendee.first_name.ilike(search_term),
                Attendee.last_name.ilike(search_term),
                Attendee.email.ilike(search_term),
                Attendee.company.ilike(search_term),
            )
        )
    
    total = query.count()
    attendees = query.offset(skip).limit(limit).all()
    
    return attendees, total


def create_attendee(db: Session, attendee_in: AttendeeCreate) -> Attendee:
    """
    Create a new attendee
    """
    # Check if attendee with email already exists
    existing_attendee = get_attendee_by_email(db, attendee_in.email)
    if existing_attendee:
        return existing_attendee
    
    db_attendee = Attendee(
        id=str(uuid.uuid4()),
        **attendee_in.dict(),
    )
    db.add(db_attendee)
    db.commit()
    db.refresh(db_attendee)
    return db_attendee


def update_attendee(db: Session, attendee_id: str, attendee_in: AttendeeUpdate) -> Optional[Attendee]:
    """
    Update an attendee
    """
    db_attendee = get_attendee(db, attendee_id)
    if not db_attendee:
        return None
    
    update_data = attendee_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_attendee, field, value)
    
    db.add(db_attendee)
    db.commit()
    db.refresh(db_attendee)
    return db_attendee


def delete_attendee(db: Session, attendee_id: str) -> bool:
    """
    Delete an attendee
    """
    db_attendee = get_attendee(db, attendee_id)
    if not db_attendee:
        return False
    
    db.delete(db_attendee)
    db.commit()
    return True


def add_attendee_to_event(db: Session, attendee_id: str, event_id: str) -> bool:
    """
    Add attendee to event
    """
    from app.models.event import Event
    from app.models.attendee import event_attendee
    
    # Check if attendee and event exist
    attendee = get_attendee(db, attendee_id)
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not attendee or not event:
        return False
    
    # Check if attendee is already associated with event
    existing = db.query(event_attendee).filter(
        event_attendee.c.attendee_id == attendee_id,
        event_attendee.c.event_id == event_id
    ).first()
    
    if existing:
        return True  # Already associated
    
    # Add association
    stmt = event_attendee.insert().values(
        attendee_id=attendee_id,
        event_id=event_id,
        checked_in=False
    )
    db.execute(stmt)
    db.commit()
    
    return True


def check_in_attendee(db: Session, attendee_id: str, event_id: str) -> bool:
    """
    Check in an attendee to an event
    """
    from app.models.attendee import event_attendee
    from datetime import datetime
    
    # Check if association exists
    existing = db.query(event_attendee).filter(
        event_attendee.c.attendee_id == attendee_id,
        event_attendee.c.event_id == event_id
    ).first()
    
    if not existing:
        return False
    
    # Update check-in status
    stmt = event_attendee.update().where(
        event_attendee.c.attendee_id == attendee_id,
        event_attendee.c.event_id == event_id
    ).values(
        checked_in=True,
        checked_in_at=datetime.utcnow()
    )
    
    db.execute(stmt)
    db.commit()
    
    return True 