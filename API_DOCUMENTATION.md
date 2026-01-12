# API Documentation

## Base URL
- **Development**: `http://localhost:8000/api/v1`
- **Production**: `https://your-api-domain.com/api/v1`

## Authentication

All endpoints (except `/auth/me`) require authentication via Bearer token in the Authorization header:

```
Authorization: Bearer <supabase_access_token>
```

The token is obtained from Supabase Auth after user login.

---

## Endpoints

### Authentication

#### `GET /auth/me`
Get current authenticated user information.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "user"
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

### Chat

#### `POST /chat/query`
Send a chat query and get AI response with RAG (Retrieval-Augmented Generation).

**Request Body:**
```json
{
  "query": "What is the main topic of the uploaded documents?",
  "conversation_id": "uuid (optional)",
  "stream": false,
  "file_upload": "document_id (optional)"
}
```

**Parameters:**
- `query` (string, required): The user's question or message
- `conversation_id` (string, optional): UUID of existing conversation to continue
- `stream` (boolean, default: false): Enable Server-Sent Events streaming
- `file_upload` (string, optional): Document ID if file was uploaded in chat

**Response (Non-streaming):**
```json
{
  "answer": "Based on the documents...",
  "citations": [
    {
      "document_id": "uuid",
      "document_title": "Document Name",
      "content": "Relevant excerpt...",
      "page_number": 1
    }
  ]
}
```

**Response (Streaming):**
Returns Server-Sent Events (SSE) stream with format:
```
data: {"type": "content", "content": "chunk of text"}
data: {"type": "citation", "citation": {...}}
data: {"type": "done"}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `401`: Unauthorized
- `500`: Server error

---

#### `POST /chat/upload-file`
Upload a file directly from chat interface.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `file` (file, required): PDF, DOCX, TXT, or MD file
  - `folder_id` (string, optional): Folder ID to upload to
  - `conversation_id` (string, optional): Conversation ID to associate with

**Response:**
```json
{
  "document_id": "uuid",
  "title": "filename.pdf",
  "status": "processing",
  "message": "File uploaded successfully. It's being processed..."
}
```

**Status Codes:**
- `200`: Upload successful
- `400`: Invalid file type or missing filename
- `401`: Unauthorized
- `500`: Upload failed

**Supported File Types:**
- PDF (`.pdf`)
- Word Documents (`.docx`)
- Text Files (`.txt`)
- Markdown (`.md`)

---

#### `POST /chat/conversations`
Create a new conversation.

**Request Body:**
```json
{
  "title": "New Chat"
}
```

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "New Chat",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `201`: Created
- `400`: Invalid request
- `401`: Unauthorized

---

#### `GET /chat/conversations`
List all conversations for the current user.

**Response:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "title": "Chat Title",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

#### `PUT /chat/conversations/{conversation_id}`
Update a conversation title.

**Request Body:**
```json
{
  "title": "Updated Title"
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Updated Title",
  ...
}
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (not the owner)
- `404`: Conversation not found
- `401`: Unauthorized

---

#### `DELETE /chat/conversations/{conversation_id}`
Delete a conversation and all its messages.

**Response:**
```json
{
  "message": "Conversation deleted successfully",
  "id": "uuid"
}
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (not the owner)
- `404`: Conversation not found
- `401`: Unauthorized

---

#### `GET /chat/conversations/{conversation_id}/messages`
Get all messages for a conversation.

**Response:**
```json
[
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "role": "user",
    "content": "User message",
    "created_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "role": "assistant",
    "content": "AI response",
    "citations": [...],
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Status Codes:**
- `200`: Success
- `404`: Conversation not found
- `401`: Unauthorized

---

### Documents

#### `POST /documents/upload`
Upload a document to the document vault.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `file` (file, required): PDF, DOCX, TXT, or MD file
  - `folder_id` (string, optional): Folder ID to upload to
  - `folder_name` (string, optional): Create new folder with this name

**Response:**
```json
{
  "id": "uuid",
  "status": "processing",
  "message": "Upload successful, ingestion started."
}
```

**Status Codes:**
- `200`: Upload successful
- `400`: Invalid file type
- `401`: Unauthorized
- `500`: Upload failed

**Note:** Document processing happens in the background. Check status via `GET /documents/{id}`.

---

#### `GET /documents`
List all documents for the current user.

**Query Parameters:**
- `folder_id` (string, optional): Filter by folder ID

**Response:**
```json
[
  {
    "id": "uuid",
    "owner_id": "uuid",
    "title": "document.pdf",
    "storage_path": "path/to/file",
    "mime_type": "application/pdf",
    "status": "completed",
    "chunk_count": 42,
    "folder_id": "uuid (optional)",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Document Status Values:**
- `processing`: Document is being processed
- `completed`: Processing finished successfully
- `failed`: Processing failed (check `error_message`)

**Status Codes:**
- `200`: Success
- `401`: Unauthorized
- `404`: Folder not found (if folder_id provided)

---

#### `DELETE /documents/{document_id}`
Delete a document and all associated chunks.

**Response:**
```json
{
  "message": "Document deleted successfully",
  "id": "uuid"
}
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (not the owner)
- `404`: Document not found
- `401`: Unauthorized

---

#### `POST /documents/{document_id}/reprocess`
Reprocess a failed document.

**Response:**
```json
{
  "message": "Document reprocessing started",
  "id": "uuid",
  "status": "processing"
}
```

**Status Codes:**
- `200`: Reprocessing started
- `400`: Document has no storage path
- `403`: Not authorized (not the owner)
- `404`: Document not found
- `401`: Unauthorized

---

### Folders

#### `GET /folders`
List folders accessible to the current user.

**Query Parameters:**
- `parent_id` (string, optional): Filter by parent folder ID (returns only children)

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Folder Name",
    "owner_id": "uuid",
    "parent_id": "uuid (optional)",
    "document_count": 5,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

#### `GET /folders/{folder_id}`
Get a specific folder by ID.

**Response:**
```json
{
  "id": "uuid",
  "name": "Folder Name",
  "owner_id": "uuid",
  "parent_id": "uuid (optional)",
  "document_count": 5,
  "children": [
    {
      "id": "uuid",
      "name": "Subfolder",
      ...
    }
  ],
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (no access)
- `404`: Folder not found
- `401`: Unauthorized

---

#### `POST /folders`
Create a new folder.

**Request Body:**
```json
{
  "name": "New Folder",
  "parent_id": "uuid (optional)",
  "allowed_roles": ["admin"] (optional),
  "allowed_users": ["user_id"] (optional)
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "New Folder",
  "owner_id": "uuid",
  "parent_id": "uuid (optional)",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `201`: Created
- `400`: Invalid request
- `403`: Not authorized (no access to parent)
- `404`: Parent folder not found
- `401`: Unauthorized

---

#### `PUT /folders/{folder_id}`
Update a folder.

**Request Body:**
```json
{
  "name": "Updated Name" (optional),
  "parent_id": "uuid (optional)",
  "allowed_roles": ["admin"] (optional),
  "allowed_users": ["user_id"] (optional)
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Updated Name",
  ...
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid request (e.g., circular reference)
- `403`: Not authorized (not owner/admin)
- `404`: Folder or parent not found
- `401`: Unauthorized

---

#### `DELETE /folders/{folder_id}`
Delete a folder and all its contents (recursive).

**Response:**
```json
{
  "message": "Folder and all contents deleted successfully",
  "id": "uuid",
  "deleted_documents": 10,
  "deleted_subfolders": 2
}
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (not the owner)
- `404`: Folder not found
- `401`: Unauthorized

**Warning:** This operation is irreversible and deletes all documents and subfolders.

---

#### `GET /folders/{folder_id}/documents`
List all documents in a folder.

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "document.pdf",
    "status": "completed",
    ...
  }
]
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (no access to folder)
- `404`: Folder not found
- `401`: Unauthorized

---

#### `GET /folders/tree/all`
Get complete folder tree structure.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Root Folder",
    "document_count": 5,
    "children": [
      {
        "id": "uuid",
        "name": "Subfolder",
        "document_count": 2,
        "children": []
      }
    ]
  }
]
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

### Admin

#### `GET /admin/users`
List all users (admin only).

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (not admin)
- `401`: Unauthorized

---

#### `POST /admin/users`
Create a new user (admin only).

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "role": "user"
}
```

**Status Codes:**
- `201`: Created
- `400`: Invalid request
- `403`: Not authorized (not admin)
- `401`: Unauthorized

---

#### `PUT /admin/users/{user_id}`
Update a user (admin only).

**Request Body:**
```json
{
  "email": "updated@example.com",
  "role": "admin"
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `403`: Not authorized (not admin)
- `404`: User not found
- `401`: Unauthorized

---

#### `DELETE /admin/users/{user_id}`
Delete a user (admin only).

**Response:**
```json
{
  "message": "User deleted successfully",
  "id": "uuid"
}
```

**Status Codes:**
- `200`: Success
- `403`: Not authorized (not admin)
- `404`: User not found
- `401`: Unauthorized

---

### Analytics

#### `GET /analytics/usage`
Get usage statistics for the current user.

**Response:**
```json
{
  "total_documents": 10,
  "total_conversations": 5,
  "total_messages": 50
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

## Error Responses

All endpoints return errors in the following format:

```json
{
  "detail": "Error message description"
}
```

### Common Status Codes

- `400 Bad Request`: Invalid request parameters or body
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Authenticated but not authorized for this operation
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error (check logs)

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limits in production.

---

## WebSocket / Streaming

The chat endpoint supports Server-Sent Events (SSE) for streaming responses:

1. Set `stream: true` in the request body
2. Connect to the endpoint
3. Receive chunks as they're generated:
   ```
   data: {"type": "content", "content": "Hello"}
   data: {"type": "content", "content": " world"}
   data: {"type": "done"}
   ```

---

## Examples

### Upload Document and Query

```bash
# 1. Upload document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  -F "folder_id=<folder_id>"

# 2. Query with RAG
curl -X POST "http://localhost:8000/api/v1/chat/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic?",
    "conversation_id": "<conversation_id>"
  }'
```

### Streaming Chat Query

```javascript
const response = await fetch('http://localhost:8000/api/v1/chat/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'Explain the document',
    stream: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.type === 'content') {
        console.log(data.content);
      }
    }
  }
}
```

---

## Changelog

### Version 1.0.0
- Initial API documentation
- Chat endpoints with streaming support
- Document upload and management
- Folder organization
- Admin endpoints
