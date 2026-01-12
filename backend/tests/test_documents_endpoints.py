"""
Tests for document endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.models.user import User
from uuid import uuid4


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


class TestDocumentUpload:
    """Tests for POST /documents/upload endpoint."""
    
    @patch('app.api.v1.endpoints.documents.deps.get_current_user')
    @patch('app.api.v1.endpoints.documents.storage_service')
    @patch('app.api.v1.endpoints.documents.get_supabase_client')
    def test_upload_document_success(self, mock_get_client, mock_storage, mock_get_user, client, mock_user):
        """Test successful document upload."""
        mock_get_user.return_value = mock_user
        mock_storage.upload_file = AsyncMock(return_value="path/to/file.pdf")
        
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_table.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        
        response = client.post(
            "/api/v1/documents/upload",
            files=files,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "processing"
    
    @patch('app.api.v1.endpoints.documents.deps.get_current_user')
    def test_upload_document_invalid_type(self, mock_get_user, client, mock_user):
        """Test uploading invalid file type."""
        mock_get_user.return_value = mock_user
        
        files = {"file": ("test.exe", b"content", "application/x-msdownload")}
        
        response = client.post(
            "/api/v1/documents/upload",
            files=files,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400


class TestDocumentList:
    """Tests for GET /documents endpoint."""
    
    @patch('app.api.v1.endpoints.documents.deps.get_current_user')
    @patch('app.api.v1.endpoints.documents.get_supabase_client')
    def test_list_documents(self, mock_get_client, mock_get_user, client, mock_user):
        """Test listing documents."""
        mock_get_user.return_value = mock_user
        
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"id": str(uuid4()), "title": "doc1.pdf"},
            {"id": str(uuid4()), "title": "doc2.pdf"}
        ]
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.get(
            "/api/v1/documents",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
    
    @patch('app.api.v1.endpoints.documents.deps.get_current_user')
    @patch('app.api.v1.endpoints.documents.get_supabase_client')
    def test_list_documents_with_folder(self, mock_get_client, mock_get_user, client, mock_user):
        """Test listing documents in a folder."""
        mock_get_user.return_value = mock_user
        
        mock_client = Mock()
        mock_table = Mock()
        # Mock folder check
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": str(uuid4()),
            "owner_id": str(mock_user.id)
        }
        # Mock documents query
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"id": str(uuid4()), "title": "doc1.pdf"}
        ]
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        folder_id = str(uuid4())
        response = client.get(
            f"/api/v1/documents?folder_id={folder_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200


class TestDocumentDelete:
    """Tests for DELETE /documents/{id} endpoint."""
    
    @patch('app.api.v1.endpoints.documents.deps.get_current_user')
    @patch('app.api.v1.endpoints.documents.get_supabase_client')
    def test_delete_document_success(self, mock_get_client, mock_get_user, client, mock_user):
        """Test successful document deletion."""
        mock_get_user.return_value = mock_user
        doc_id = str(uuid4())
        
        mock_client = Mock()
        mock_table = Mock()
        # Mock document fetch
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": doc_id,
            "owner_id": str(mock_user.id),
            "storage_path": "path/to/file.pdf"
        }
        # Mock storage deletion
        mock_storage = Mock()
        mock_storage.from_.return_value.remove.return_value = None
        mock_client.storage = mock_storage
        # Mock document deletion
        mock_table.delete.return_value.eq.return_value.execute.return_value.data = [{"id": doc_id}]
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"
    
    @patch('app.api.v1.endpoints.documents.deps.get_current_user')
    @patch('app.api.v1.endpoints.documents.get_supabase_client')
    def test_delete_document_not_found(self, mock_get_client, mock_get_user, client, mock_user):
        """Test deleting non-existent document."""
        mock_get_user.return_value = mock_user
        
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.delete(
            f"/api/v1/documents/{uuid4()}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 404
    
    @patch('app.api.v1.endpoints.documents.deps.get_current_user')
    @patch('app.api.v1.endpoints.documents.get_supabase_client')
    def test_delete_document_unauthorized(self, mock_get_client, mock_get_user, client, mock_user):
        """Test deleting document owned by another user."""
        mock_get_user.return_value = mock_user
        
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": str(uuid4()),
            "owner_id": str(uuid4()),  # Different user
            "storage_path": "path/to/file.pdf"
        }
        mock_client.table.return_value = mock_table
        mock_get_client.return_value = mock_client
        
        response = client.delete(
            f"/api/v1/documents/{uuid4()}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 403
