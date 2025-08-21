"""
Tests for main app functionality
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to EventTicketing API"}


@pytest.mark.asyncio
async def test_root_endpoint_async(async_client: AsyncClient):
    """Test the root endpoint with async client."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to EventTicketing API"}


def test_openapi_json(client: TestClient):
    """Test that OpenAPI JSON is available."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    openapi_data = response.json()
    assert "openapi" in openapi_data
    assert "info" in openapi_data
    assert openapi_data["info"]["title"] == "EventTicketing"