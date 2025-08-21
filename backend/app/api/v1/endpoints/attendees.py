from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas, services
from app.api import deps
from app.models.user import User, UserRole

router = APIRouter()


@router.get("/", response_model=schemas.AttendeeList)
def get_attendees(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: User = Depends(deps.get_current_user_organizer),
) -> Any:
    """
    Get list of attendees (organizers and admins only)
    """
    attendees, total = services.get_attendees(
        db=db, skip=skip, limit=limit, search=search
    )
    return {
        "attendees": attendees,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit
    }


@router.get("/event/{event_id}", response_model=schemas.AttendeeList)
def get_event_attendees(
    event_id: str,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get attendees for a specific event
    """
    # Check if user is event owner or has role permissions
    event = services.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check permissions: either admin/organizer role or the event owner
    is_admin_or_organizer = current_user.role in [UserRole.ADMIN, UserRole.ORGANIZER]
    is_event_owner = event.owner_id == current_user.id
    
    if not (is_admin_or_organizer or is_event_owner):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    attendees, total = services.get_attendees_by_event(
        db=db, event_id=event_id, skip=skip, limit=limit, search=search
    )
    
    return {
        "attendees": attendees,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit
    }


@router.get("/{attendee_id}", response_model=schemas.Attendee)
def get_attendee(
    attendee_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get attendee by ID
    """
    attendee = services.get_attendee(db=db, attendee_id=attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    # Only allow access to the user's own attendee record or admins/organizers
    is_admin_or_organizer = current_user.role in [UserRole.ADMIN, UserRole.ORGANIZER]
    is_own_record = attendee.user_id == current_user.id
    
    if not (is_admin_or_organizer or is_own_record):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return attendee


@router.post("/", response_model=schemas.Attendee)
def create_attendee(
    *,
    db: Session = Depends(deps.get_db),
    attendee_in: schemas.AttendeeCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new attendee
    """
    # If user is creating their own attendee profile, ensure user_id is set
    if not attendee_in.user_id and current_user.role == UserRole.ATTENDEE:
        attendee_in.user_id = current_user.id
    
    # Only organizers/admins can create attendee profiles for others
    if (attendee_in.user_id != current_user.id and 
            current_user.role not in [UserRole.ADMIN, UserRole.ORGANIZER]):
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions to create attendee profile for another user"
        )
    
    attendee = services.create_attendee(db=db, attendee_in=attendee_in)
    return attendee


@router.put("/{attendee_id}", response_model=schemas.Attendee)
def update_attendee(
    *,
    db: Session = Depends(deps.get_db),
    attendee_id: str,
    attendee_in: schemas.AttendeeUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update an attendee
    """
    attendee = services.get_attendee(db=db, attendee_id=attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    # Only allow updating the user's own attendee record or admins/organizers
    is_admin_or_organizer = current_user.role in [UserRole.ADMIN, UserRole.ORGANIZER]
    is_own_record = attendee.user_id == current_user.id
    
    if not (is_admin_or_organizer or is_own_record):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    attendee = services.update_attendee(db=db, attendee_id=attendee_id, attendee_in=attendee_in)
    return attendee


@router.delete("/{attendee_id}")
def delete_attendee(
    *,
    db: Session = Depends(deps.get_db),
    attendee_id: str,
    current_user: User = Depends(deps.get_current_user_admin),
) -> Any:
    """
    Delete an attendee (admin only)
    """
    attendee = services.get_attendee(db=db, attendee_id=attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    services.delete_attendee(db=db, attendee_id=attendee_id)
    return {"message": "Attendee successfully deleted"}


@router.post("/{attendee_id}/check-in/{event_id}")
def check_in_attendee(
    *,
    db: Session = Depends(deps.get_db),
    attendee_id: str,
    event_id: str,
    current_user: User = Depends(deps.get_current_user_organizer),
) -> Any:
    """
    Check in an attendee to an event (organizers and admins only)
    """
    success = services.check_in_attendee(db=db, attendee_id=attendee_id, event_id=event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Attendee or event not found")
    
    return {"message": "Attendee successfully checked in"} 