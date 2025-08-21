from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.organization import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationMember,
)
from app.services.organization import organization_service
from app.services.user import user_service

router = APIRouter()


@router.get("/", response_model=List[Organization])
async def read_organizations(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve organizations that the current user is a member of.
    """
    organizations = await organization_service.get_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return organizations


@router.post("/", response_model=Organization)
async def create_organization(
    *,
    db: AsyncSession = Depends(get_db),
    organization_in: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create new organization.
    """
    # Check if slug already exists
    existing_org = await organization_service.get_by_slug(db, slug=organization_in.slug)
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this slug already exists",
        )
    
    organization = await organization_service.create(
        db=db, obj_in=organization_in, owner=current_user
    )
    return organization


@router.get("/my", response_model=List[Organization])
async def read_owned_organizations(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve organizations owned by the current user.
    """
    organizations = await organization_service.get_multi_by_owner(
        db=db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return organizations


@router.get("/{org_id}", response_model=Organization)
async def read_organization(
    *,
    db: AsyncSession = Depends(get_db),
    org_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get organization by ID.
    """
    organization = await organization_service.get(db=db, id=org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    # Check if user is a member of this organization
    if current_user not in organization.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this organization",
        )
    
    return organization


@router.put("/{org_id}", response_model=Organization)
async def update_organization(
    *,
    db: AsyncSession = Depends(get_db),
    org_id: str,
    organization_in: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update an organization.
    """
    organization = await organization_service.get(db=db, id=org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    # Check if user is an admin of this organization
    # TODO: Implement proper role checking
    if current_user not in organization.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this organization",
        )
    
    organization = await organization_service.update(
        db=db, db_obj=organization, obj_in=organization_in
    )
    return organization


@router.post("/{org_id}/members", response_model=dict)
async def add_member(
    *,
    db: AsyncSession = Depends(get_db),
    org_id: str,
    user_id: str,
    role: str = Query("member", description="Role for the new member"),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Add a member to the organization.
    """
    organization = await organization_service.get(db=db, id=org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    # Check if user is an admin of this organization
    # TODO: Implement proper role checking
    if current_user not in organization.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to add members to this organization",
        )
    
    # Check if user exists
    user = await user_service.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Add user to organization
    await organization_service.add_user_to_org(
        db=db, org_id=org_id, user_id=user_id, role=role
    )
    
    return {"msg": "User added to organization"}


@router.delete("/{org_id}/members/{user_id}", response_model=dict)
async def remove_member(
    *,
    db: AsyncSession = Depends(get_db),
    org_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Remove a member from the organization.
    """
    organization = await organization_service.get(db=db, id=org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    # Check if user is an admin of this organization
    # TODO: Implement proper role checking
    if current_user not in organization.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to remove members from this organization",
        )
    
    # Remove user from organization
    await organization_service.remove_user_from_org(
        db=db, org_id=org_id, user_id=user_id
    )
    
    return {"msg": "User removed from organization"} 