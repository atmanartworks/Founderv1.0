# Simplified Database Schema

## Overview

This schema is designed for a **single-user system** with no RBAC (Role-Based Access Control). All authenticated users can access all documents.

## Key Changes from Original Schema

1. **No Folders** - Removed folder hierarchy and permissions
2. **No RBAC** - Removed role-based access control
3. **No Document Permissions** - All documents accessible to all authenticated users
4. **Simplified RLS** - Minimal policies for single-user system
5. **Simplified Citations** - No highlighting offsets needed (just document name + page)

## Tables

### `users`
- Basic user info (id, email, full_name)
- `role` field kept for compatibility but not used for access control

### `documents`
- Document metadata
- `status`: 'processing', 'completed', 'failed'
- `chunk_count`: Number of chunks created
- `error_message`: Error details if processing failed
- No `folder_id`, `allowed_roles`, or `allowed_users`

### `document_chunks`
- Chunks for RAG
- Vector embeddings (1536 dimensions)
- Page numbers and character offsets (for compatibility, not used for highlighting)

### `conversations`
- Chat conversations
- Linked to user_id

### `messages`
- Chat messages
- Citations stored as JSONB array

### `conversation_logs`
- Developer analytics
- Full conversation details for future assistance
- Includes mode (RAG/general), tokens used, etc.

## Functions

### `search_document_chunks`
- Simplified vector search
- No user filtering (single user system)
- Returns top K chunks by similarity

## RLS Policies

- **Minimal policies** - Single user system
- Authenticated users can access all documents
- Users can only access their own conversations
- Service role has full access for backend operations

## Usage

1. Run `reset_and_recreate.sql` in Supabase SQL Editor
2. This will drop all existing tables and recreate the simplified schema
3. All data will be lost - backup first if needed!

## Migration Notes

- Old schema had folders, RBAC, complex permissions
- New schema is flat - all documents accessible
- Citations simplified (no highlighting)
- Vector search simplified (no user filtering)

