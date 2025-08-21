"""
Tests for authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


@pytest.fixture
async def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
async def created_user(db_session: AsyncSession, test_user_data):
    """Create a test user in the database."""
    from app.services.user import create_user
    
    user_create = UserCreate(**test_user_data)
    user = await create_user(db_session, user_create)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def test_register_user(client: TestClient):
    """Test user registration endpoint."""
    user_data = {
        "email": "newuser@example.com",
        "password": "newpassword123",
        "full_name": "New User"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert "id" in data
    assert "password" not in data  # Password should not be returned


def test_register_existing_user(client: TestClient, test_user_data):
    """Test registration with existing email fails."""
    # First registration
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Second registration with same email should fail
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, created_user, test_user_data):
    """Test successful login."""
    login_data = {
        "username": test_user_data["email"],  # OAuth2 uses 'username' field
        "password": test_user_data["password"]
    }
    
    response = await async_client.post(
        "/api/v1/auth/login", 
        data=login_data,  # OAuth2 expects form data
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient):
    """Test login with invalid credentials."""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    
    response = await async_client.post(
        "/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_password_validation():
    """Test password hashing and verification."""
    password = "testpassword123"
    
    # Test that password verification works
    from app.core.security import get_password_hash
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_access_token_creation():
    """Test JWT token creation and validation."""
    user_id = 1
    token = create_access_token(data={"sub": str(user_id)})
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0