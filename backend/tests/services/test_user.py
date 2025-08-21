"""
Tests for user service
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user import user_service


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test user creation service."""
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User"
    )
    
    user = await user_service.create(db_session, user_data)
    await db_session.commit()
    
    assert user.email == user_data.email
    assert user.full_name == user_data.full_name
    assert user.id is not None
    assert user.hashed_password != user_data.password  # Should be hashed
    assert user.is_active is True
    assert user.is_superuser is False


@pytest.mark.asyncio
async def test_get_user_by_email(db_session: AsyncSession):
    """Test getting user by email."""
    # Create a user first
    user_data = UserCreate(
        email="findme@example.com",
        password="password123",
        full_name="Find Me"
    )
    created_user = await user_service.create(db_session, user_data)
    await db_session.commit()
    
    # Find the user
    found_user = await user_service.get_by_email(db_session, email="findme@example.com")
    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.email == "findme@example.com"
    
    # Test with non-existent email
    not_found = await user_service.get_by_email(db_session, email="notfound@example.com")
    assert not_found is None


@pytest.mark.asyncio
async def test_update_user(db_session: AsyncSession):
    """Test user update service."""
    # Create a user first
    user_data = UserCreate(
        email="update@example.com",
        password="password123",
        full_name="Original Name"
    )
    user = await user_service.create(db_session, user_data)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Update the user
    update_data = UserUpdate(
        full_name="Updated Name",
        is_active=False
    )
    
    updated_user = await user_service.update(db_session, db_obj=user, obj_in=update_data)
    await db_session.commit()
    await db_session.refresh(updated_user)
    
    assert updated_user.full_name == "Updated Name"
    assert updated_user.is_active is False
    assert updated_user.email == user_data.email  # Should remain unchanged


@pytest.mark.asyncio
async def test_create_superuser(db_session: AsyncSession):
    """Test creating a superuser."""
    user_data = UserCreate(
        email="admin@example.com",
        password="adminpassword123",
        full_name="Admin User"
    )
    
    # Create superuser by setting is_superuser=True
    user = await create_user(db_session, user_data, is_superuser=True)
    await db_session.commit()
    
    assert user.is_superuser is True
    assert user.is_active is True