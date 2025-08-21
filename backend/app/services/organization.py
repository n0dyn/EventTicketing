from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.organization import Organization
from app.models.user import User, user_organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    async def get(self, db: AsyncSession, id: str) -> Optional[Organization]:
        """
        Get organization by ID
        """
        result = await db.execute(select(Organization).where(Organization.id == id))
        return result.scalars().first()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[Organization]:
        """
        Get organization by slug
        """
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalars().first()

    async def create(
        self, db: AsyncSession, *, obj_in: OrganizationCreate, owner: User
    ) -> Organization:
        """
        Create a new organization
        """
        db_obj = Organization(
            name=obj_in.name,
            slug=obj_in.slug,
            description=obj_in.description,
            website=obj_in.website,
            logo_url=obj_in.logo_url,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
        )
        
        # Add the owner to the organization with admin role
        db_obj.members.append(owner)
        
        # Insert the relationship with role
        stmt = user_organization.insert().values(
            user_id=owner.id, organization_id=db_obj.id, role="admin"
        )
        await db.execute(stmt)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Organization,
        obj_in: Union[OrganizationUpdate, Dict[str, Any]]
    ) -> Organization:
        """
        Update an organization
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Organization]:
        """
        Get multiple organizations with pagination
        """
        result = await db.execute(select(Organization).offset(skip).limit(limit))
        return result.scalars().all()

    async def get_multi_by_owner(
        self, db: AsyncSession, *, owner_id: str, skip: int = 0, limit: int = 100
    ) -> List[Organization]:
        """
        Get multiple organizations by owner
        """
        result = await db.execute(
            select(Organization)
            .join(user_organization)
            .where(user_organization.c.user_id == owner_id)
            .where(user_organization.c.role == "admin")
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_user(
        self, db: AsyncSession, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Organization]:
        """
        Get organizations that a user is a member of
        """
        result = await db.execute(
            select(Organization)
            .join(user_organization)
            .where(user_organization.c.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def add_user_to_org(
        self, db: AsyncSession, *, org_id: str, user_id: str, role: str = "member"
    ) -> bool:
        """
        Add a user to an organization
        """
        stmt = user_organization.insert().values(
            user_id=user_id, organization_id=org_id, role=role
        )
        await db.execute(stmt)
        await db.commit()
        return True

    async def remove_user_from_org(
        self, db: AsyncSession, *, org_id: str, user_id: str
    ) -> bool:
        """
        Remove a user from an organization
        """
        stmt = user_organization.delete().where(
            user_organization.c.user_id == user_id,
            user_organization.c.organization_id == org_id,
        )
        await db.execute(stmt)
        await db.commit()
        return True

    async def update_user_role(
        self, db: AsyncSession, *, org_id: str, user_id: str, role: str
    ) -> bool:
        """
        Update a user's role in an organization
        """
        stmt = (
            user_organization.update()
            .where(
                user_organization.c.user_id == user_id,
                user_organization.c.organization_id == org_id,
            )
            .values(role=role)
        )
        await db.execute(stmt)
        await db.commit()
        return True


organization_service = OrganizationService() 