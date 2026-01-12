"""
Tests for custom exception classes.
"""
import pytest
from app.core.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    FileUploadError,
    DatabaseError,
    CircularReferenceError
)


class TestValidationError:
    """Tests for ValidationError."""
    
    def test_validation_error_basic(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert error.status_code == 400
        assert error.detail == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
    
    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        error = ValidationError("Invalid email", field="email")
        assert error.status_code == 400
        assert error.detail == "Invalid email"
        assert error.field == "email"
        assert error.error_code == "VALIDATION_ERROR_EMAIL"


class TestAuthenticationError:
    """Tests for AuthenticationError."""
    
    def test_authentication_error(self):
        """Test authentication error."""
        error = AuthenticationError("Invalid token")
        assert error.status_code == 401
        assert error.detail == "Invalid token"
        assert error.error_code == "AUTHENTICATION_ERROR"
    
    def test_authentication_error_default(self):
        """Test authentication error with default message."""
        error = AuthenticationError()
        assert error.status_code == 401
        assert error.detail == "Authentication failed"


class TestAuthorizationError:
    """Tests for AuthorizationError."""
    
    def test_authorization_error(self):
        """Test authorization error."""
        error = AuthorizationError("Access denied")
        assert error.status_code == 403
        assert error.detail == "Access denied"
        assert error.error_code == "AUTHORIZATION_ERROR"


class TestNotFoundError:
    """Tests for NotFoundError."""
    
    def test_not_found_error_basic(self):
        """Test not found error without ID."""
        error = NotFoundError("Document")
        assert error.status_code == 404
        assert error.detail == "Document not found"
        assert error.resource == "Document"
        assert error.resource_id is None
    
    def test_not_found_error_with_id(self):
        """Test not found error with ID."""
        resource_id = "123"
        error = NotFoundError("Document", resource_id)
        assert error.status_code == 404
        assert error.detail == f"Document with id '{resource_id}' not found"
        assert error.resource == "Document"
        assert error.resource_id == resource_id


class TestFileUploadError:
    """Tests for FileUploadError."""
    
    def test_file_upload_error(self):
        """Test file upload error."""
        error = FileUploadError("Upload failed", reason="File too large")
        assert error.status_code == 400
        assert "Upload failed" in error.detail
        assert "File too large" in error.detail
        assert error.reason == "File too large"
        assert error.error_code == "FILE_UPLOAD_ERROR"


class TestDatabaseError:
    """Tests for DatabaseError."""
    
    def test_database_error(self):
        """Test database error."""
        error = DatabaseError("Connection failed", operation="query")
        assert error.status_code == 500
        assert "Database query failed" in error.detail
        assert error.operation == "query"
        assert error.error_code == "DATABASE_ERROR"


class TestCircularReferenceError:
    """Tests for CircularReferenceError."""
    
    def test_circular_reference_error(self):
        """Test circular reference error."""
        error = CircularReferenceError("Folder cannot be its own parent")
        assert error.status_code == 400
        assert error.detail == "Folder cannot be its own parent"
        assert error.error_code == "CIRCULAR_REFERENCE_ERROR"
