# Testing Guide

This directory contains tests for the FounderGPT API backend.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_chat_endpoints.py   # Tests for chat endpoints
├── test_documents_endpoints.py  # Tests for document endpoints
└── test_exceptions.py      # Tests for custom exceptions
```

## Running Tests

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-mock
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_chat_endpoints.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage

```bash
pip install pytest-cov
pytest --cov=app --cov-report=html
```

## Test Categories

### Unit Tests
- Test individual functions and classes in isolation
- Use mocks to isolate dependencies
- Fast execution

### Integration Tests
- Test endpoints with mocked dependencies
- Verify request/response flow
- Test error handling

## Writing Tests

### Example Test

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@patch('app.api.v1.endpoints.chat.deps.get_current_user')
def test_endpoint(client, mock_get_user):
    mock_get_user.return_value = mock_user
    
    response = client.get("/api/v1/endpoint")
    assert response.status_code == 200
```

### Best Practices

1. **Use Fixtures**: Define reusable fixtures in `conftest.py`
2. **Mock External Dependencies**: Mock database, storage, and external APIs
3. **Test Edge Cases**: Test error conditions, invalid inputs, unauthorized access
4. **Keep Tests Isolated**: Each test should be independent
5. **Use Descriptive Names**: Test names should describe what they test

## Test Coverage Goals

- **Critical Endpoints**: 80%+ coverage
- **Error Handling**: All error paths tested
- **Authentication/Authorization**: All permission checks tested

## Continuous Integration

Tests should run automatically on:
- Pull requests
- Commits to main branch
- Before deployment

## Mocking Guidelines

### Database Operations
```python
@patch('app.api.v1.endpoints.chat.get_supabase_client')
def test_with_db(mock_get_client):
    mock_client = Mock()
    mock_table = Mock()
    mock_table.select.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value = mock_table
    mock_get_client.return_value = mock_client
```

### Async Functions
```python
from unittest.mock import AsyncMock

mock_service.method = AsyncMock(return_value=result)
```

### File Uploads
```python
files = {"file": ("test.pdf", b"content", "application/pdf")}
response = client.post("/endpoint", files=files)
```

## Common Test Patterns

### Testing Authentication
```python
def test_requires_auth(client):
    response = client.get("/api/v1/protected")
    assert response.status_code == 401
```

### Testing Authorization
```python
@patch('app.api.v1.endpoints.chat.deps.get_current_user')
def test_unauthorized_access(mock_get_user, client):
    mock_get_user.return_value = other_user
    response = client.delete("/api/v1/resource/123")
    assert response.status_code == 403
```

### Testing Validation
```python
def test_invalid_input(client):
    response = client.post("/api/v1/endpoint", json={"invalid": "data"})
    assert response.status_code == 422
```

## Troubleshooting

### Tests Failing Due to Imports
- Ensure `PYTHONPATH` includes the backend directory
- Run from the backend directory: `cd backend && pytest`

### Async Test Issues
- Use `pytest-asyncio` for async tests
- Mark async tests with `@pytest.mark.asyncio`

### Mock Not Working
- Check import paths match exactly
- Use `patch.object` for instance methods
- Verify mock is applied before function call
