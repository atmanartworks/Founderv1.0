"""
Pytest configuration and fixtures for testing.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from app.main import app
from app.models.user import User
from uuid import uuid4


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        role="user"
    )


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        role="admin"
    )


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table.return_value = mock_table
    return mock_client


@pytest.fixture
def mock_get_current_user(mock_user):
    """Mock the get_current_user dependency."""
    async def _get_current_user():
        return mock_user
    return _get_current_user


@pytest.fixture
def mock_get_current_admin(mock_admin_user):
    """Mock the get_current_user dependency for admin."""
    async def _get_current_admin():
        return mock_admin_user
    return _get_current_admin
