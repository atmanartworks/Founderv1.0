"""
Custom exception classes for better error handling across the application.
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class BaseAPIException(HTTPException):
    """Base exception class for all API exceptions."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class ValidationError(BaseAPIException):
    """Raised when request validation fails."""
    
    def __init__(self, detail: str, field: Optional[str] = None):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )
        self.field = field


class AuthenticationError(BaseAPIException):
    """Raised when authentication fails."""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(BaseAPIException):
    """Raised when user is authenticated but not authorized."""
    
    def __init__(self, detail: str = "You don't have permission to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTHORIZATION_ERROR"
        )


class NotFoundError(BaseAPIException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND"
        )
        self.resource = resource
        self.resource_id = resource_id


class ConflictError(BaseAPIException):
    """Raised when a resource conflict occurs (e.g., duplicate)."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT_ERROR"
        )


class FileUploadError(BaseAPIException):
    """Raised when file upload fails."""
    
    def __init__(self, detail: str, reason: Optional[str] = None):
        if reason:
            detail = f"{detail}: {reason}"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="FILE_UPLOAD_ERROR"
        )
        self.reason = reason


class DocumentProcessingError(BaseAPIException):
    """Raised when document processing fails."""
    
    def __init__(self, document_id: str, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed for document {document_id}: {detail}",
            error_code="DOCUMENT_PROCESSING_ERROR"
        )
        self.document_id = document_id


class StorageError(BaseAPIException):
    """Raised when storage operations fail."""
    
    def __init__(self, detail: str, operation: Optional[str] = None):
        if operation:
            detail = f"Storage {operation} failed: {detail}"
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="STORAGE_ERROR"
        )
        self.operation = operation


class DatabaseError(BaseAPIException):
    """Raised when database operations fail."""
    
    def __init__(self, detail: str, operation: Optional[str] = None):
        if operation:
            detail = f"Database {operation} failed: {detail}"
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR"
        )
        self.operation = operation


class AIProviderError(BaseAPIException):
    """Raised when AI provider API calls fail."""
    
    def __init__(self, provider: str, detail: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{provider} API error: {detail}",
            error_code="AI_PROVIDER_ERROR"
        )
        self.provider = provider


class RateLimitError(BaseAPIException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_ERROR",
            headers={"Retry-After": "60"}
        )


class CircularReferenceError(BaseAPIException):
    """Raised when a circular reference is detected (e.g., folder hierarchy)."""
    
    def __init__(self, detail: str = "Circular reference detected"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="CIRCULAR_REFERENCE_ERROR"
        )
