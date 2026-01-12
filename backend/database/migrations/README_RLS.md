# Row-Level Security (RLS) Policies - Implementation Guide

## Overview

This migration implements comprehensive Row-Level Security (RLS) policies for all tables in FounderGPT. RLS provides database-level security enforcement, ensuring that users can only access data they're authorized to see, even if they bypass application-level checks.

## Important Notes

### Current Architecture

**The backend currently uses `service_role_key` which bypasses RLS.** This is intentional for backend operations that need full access. However, these policies will:

1. **Protect against direct database access** - If someone accesses the database directly with user tokens
2. **Enable future frontend direct access** - If we switch to user-scoped clients
3. **Provide defense in depth** - Multiple layers of security

### Service Role vs User Tokens

- **Service Role**: Bypasses RLS, used by backend API
- **User Tokens**: Enforced by RLS, used by frontend direct access (if implemented)

## Policy Structure

### Helper Functions

1. **`get_user_role(user_id)`** - Gets user's role from public.users
2. **`is_admin(user_id)`** - Checks if user is admin
3. **`has_folder_access(folder_id, user_id)`** - Checks folder permissions
4. **`has_document_access(document_id, user_id)`** - Checks document permissions

### Policy Types

Each table has policies for:
- **SELECT** - Who can read
- **INSERT** - Who can create
- **UPDATE** - Who can modify
- **DELETE** - Who can remove

## Table-Specific Policies

### Users Table
- Users can read their own profile
- Admins can read all users
- Users can update their own profile (but not role)
- Admins can update any user
- Service role has full access

### Folders Table
- Users can view folders they have access to (owner, role, or explicit permission)
- Users can create folders (become owner)
- Users can update/delete folders they own
- Admins can manage all folders
- Service role has full access

### Documents Table
- Users can view documents they have access to (owner, role, explicit permission, or folder access)
- Users can create documents (become owner)
- Users can update/delete documents they own
- Admins can manage all documents
- Service role has full access

### Document Chunks Table
- Users can view chunks from documents they have access to
- Service role has full access (for ingestion)

### Conversations Table
- Users can view/manage their own conversations
- Admins can view all conversations
- Service role has full access

### Messages Table
- Users can view/create messages in their own conversations
- Admins can view all messages
- Service role has full access

### Conversation Logs Table
- Users can read their own logs
- Admins can read all logs
- Service role has full access (for logging)

### Audit Logs Table
- Users can read their own audit logs
- Admins can read all audit logs
- Service role has full access (for logging)

## Access Control Logic

### Folder Access
A user has access to a folder if:
1. User is admin, OR
2. User is the owner, OR
3. User's role is in `allowed_roles`, OR
4. User's ID is in `allowed_users`

### Document Access
A user has access to a document if:
1. User is admin, OR
2. User is the owner, OR
3. User's role is in document's `allowed_roles`, OR
4. User's ID is in document's `allowed_users`, OR
5. Document is in a folder user has access to

## Testing RLS Policies

### Test as Regular User

```sql
-- Set role to authenticated user
SET ROLE authenticated;
SET request.jwt.claim.sub = 'user-uuid-here';

-- Try to select documents
SELECT * FROM public.documents;
-- Should only return documents user has access to

-- Try to select all users
SELECT * FROM public.users;
-- Should only return own profile
```

### Test as Admin

```sql
-- Set role to authenticated user with admin role
SET ROLE authenticated;
SET request.jwt.claim.sub = 'admin-uuid-here';

-- Update user in public.users to have admin role first
UPDATE public.users SET role = 'admin' WHERE id = 'admin-uuid-here';

-- Try to select all documents
SELECT * FROM public.documents;
-- Should return all documents
```

### Test Service Role

```sql
-- Set role to service_role
SET ROLE service_role;

-- Try to select all documents
SELECT * FROM public.documents;
-- Should return all documents (bypasses RLS)
```

## Migration Instructions

1. **Backup Database** - Always backup before running migrations
2. **Run in Supabase SQL Editor** - Copy entire migration file
3. **Verify Policies** - Check that policies were created:
   ```sql
   SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
   FROM pg_policies
   WHERE schemaname = 'public'
   ORDER BY tablename, policyname;
   ```
4. **Test Access** - Test with different user roles
5. **Monitor** - Watch for any access issues

## Troubleshooting

### Policies Not Working

1. **Check RLS is enabled**:
   ```sql
   SELECT tablename, rowsecurity 
   FROM pg_tables 
   WHERE schemaname = 'public';
   ```

2. **Check policies exist**:
   ```sql
   SELECT * FROM pg_policies WHERE schemaname = 'public';
   ```

3. **Check function permissions**:
   ```sql
   SELECT proname, proacl FROM pg_proc WHERE proname LIKE '%user_role%';
   ```

### Access Denied Errors

1. **Verify user role**:
   ```sql
   SELECT * FROM public.users WHERE id = 'user-uuid';
   ```

2. **Check folder/document permissions**:
   ```sql
   SELECT * FROM public.folders WHERE id = 'folder-uuid';
   SELECT * FROM public.documents WHERE id = 'doc-uuid';
   ```

3. **Test helper functions**:
   ```sql
   SELECT public.is_admin('user-uuid');
   SELECT public.has_folder_access('folder-uuid', 'user-uuid');
   ```

## Security Considerations

### Defense in Depth

RLS provides an additional security layer:
- **Application Level**: Backend API checks permissions
- **Database Level**: RLS policies enforce access
- **Network Level**: Firewall and VPN restrictions

### Service Role Security

The service role key should be:
- Stored securely (environment variables)
- Never exposed to frontend
- Rotated regularly
- Monitored for usage

### User Token Security

If using user tokens:
- Tokens expire automatically
- Revoked on logout
- Scoped to user's permissions
- Validated by Supabase Auth

## Future Enhancements

1. **Organization-Level Policies** - Multi-tenant support
2. **Time-Based Access** - Temporary permissions
3. **Audit Trail** - Log all RLS policy checks
4. **Performance Optimization** - Index policies for faster checks
5. **Dynamic Policies** - Policies based on custom rules

## Related Files

- `backend/database/schema.sql` - Base schema
- `backend/database/migrations/add_comprehensive_rls_policies.sql` - This migration
- `backend/app/api/deps.py` - Authentication and authorization
- `backend/app/api/v1/endpoints/folders.py` - Folder permission checks
- `backend/app/api/v1/endpoints/documents.py` - Document permission checks

---

**Status**: ✅ Implemented
**Last Updated**: 2024-12-XX

