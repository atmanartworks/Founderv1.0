"""
Tests for chat endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.models.user import User
from uuid import uuid4
import json


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        role="user"
    )


class TestChatQuery:
    """Tests for POST /chat/query endpoint."""
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    @patch('app.api.v1.endpoints.chat.chat_service')
    def test_chat_query_success(self, mock_chat_service, mock_get_user, client, mock_user):
        """Test successful chat query."""
        mock_get_user.return_value = mock_user
        mock_chat_service.generate_response = AsyncMock(return_value={
            "answer": "Test response",
            "citations": []
        })
        
        response = client.post(
            "/api/v1/chat/query",
            json={
                "query": "Test question",
                "stream": False
            },
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "Test response"
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    def test_chat_query_unauthorized(self, mock_get_user, client):
        """Test chat query without authentication."""
        mock_get_user.side_effect = Exception("Unauthorized")
        
        response = client.post(
            "/api/v1/chat/query",
            json={"query": "Test question"}
        )
        
        assert response.status_code == 401 or response.status_code == 403
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    def test_chat_query_missing_query(self, mock_get_user, client, mock_user):
        """Test chat query with missing query field."""
        mock_get_user.return_value = mock_user
        
        response = client.post(
            "/api/v1/chat/query",
            json={},
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 422  # Validation error


class TestConversationEndpoints:
    """Tests for conversation CRUD endpoints."""
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    @patch('app.api.v1.endpoints.chat.get_supabase_client')
    def test_create_conversation(self, mock_get_client, mock_get_user, client, mock_user):
        """Test creating a conversation."""
        mock_get_user.return_value = mock_user
        mock_client = Mock()
        mock_table = Mock()
        mock_table.insert.return_value.execute.return_value.data = [{
            "id": str(uuid4()),
            "user_id": str(mock_user.id),
            "title": "Test Chat"
        }]
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test Chat"},
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Chat"
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    @patch('app.api.v1.endpoints.chat.get_supabase_client')
    def test_list_conversations(self, mock_get_client, mock_get_user, client, mock_user):
        """Test listing conversations."""
        mock_get_user.return_value = mock_user
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"id": str(uuid4()), "title": "Chat 1"},
            {"id": str(uuid4()), "title": "Chat 2"}
        ]
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.get(
            "/api/v1/chat/conversations",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    @patch('app.api.v1.endpoints.chat.get_supabase_client')
    def test_update_conversation_not_found(self, mock_get_client, mock_get_user, client, mock_user):
        """Test updating a non-existent conversation."""
        mock_get_user.return_value = mock_user
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.put(
            f"/api/v1/chat/conversations/{uuid4()}",
            json={"title": "Updated"},
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 404
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    @patch('app.api.v1.endpoints.chat.get_supabase_client')
    def test_delete_conversation_unauthorized(self, mock_get_client, mock_get_user, client, mock_user):
        """Test deleting a conversation owned by another user."""
        mock_get_user.return_value = mock_user
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),  # Different user
            "title": "Other User's Chat"
        }
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.delete(
            f"/api/v1/chat/conversations/{uuid4()}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 403


class TestFileUpload:
    """Tests for file upload endpoint."""
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    @patch('app.api.v1.endpoints.chat.StorageService')
    @patch('app.api.v1.endpoints.chat.get_supabase_client')
    def test_upload_file_success(self, mock_get_client, mock_storage, mock_get_user, client, mock_user):
        """Test successful file upload."""
        mock_get_user.return_value = mock_user
        
        # Mock storage service
        mock_storage_instance = Mock()
        mock_storage_instance.upload_file = AsyncMock(return_value="path/to/file.pdf")
        mock_storage.return_value = mock_storage_instance
        
        # Mock database
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_table.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        # Create a mock file
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        
        response = client.post(
            "/api/v1/chat/upload-file",
            files=files,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["status"] == "processing"
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    def test_upload_file_invalid_type(self, mock_get_user, client, mock_user):
        """Test uploading an invalid file type."""
        mock_get_user.return_value = mock_user
        
        files = {"file": ("test.exe", b"fake content", "application/x-msdownload")}
        
        response = client.post(
            "/api/v1/chat/upload-file",
            files=files,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    @patch('app.api.v1.endpoints.chat.deps.get_current_user')
    def test_upload_file_missing_filename(self, mock_get_user, client, mock_user):
        """Test uploading a file without filename."""
        mock_get_user.return_value = mock_user
        
        files = {"file": ("", b"content", "application/pdf")}
        
        response = client.post(
            "/api/v1/chat/upload-file",
            files=files,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400
