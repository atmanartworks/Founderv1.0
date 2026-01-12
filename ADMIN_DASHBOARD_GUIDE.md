# Admin Dashboard - Implementation Guide

## Overview

The Admin Dashboard provides a comprehensive interface for managing users, folders, documents, and viewing platform statistics. Only users with the `admin` role can access this dashboard.

## Features

### ✅ Implemented

1. **Statistics Dashboard**
   - Total users count
   - Total documents count
   - Total conversations count
   - Total folders count
   - Documents by status breakdown
   - Users by role breakdown

2. **User Management**
   - List all users
   - Create new users
   - Update user roles (user, manager, admin)
   - Update user full names
   - Delete users (with confirmation)

3. **Folder Management**
   - List all folders
   - Create new folders
   - View folder permissions
   - Edit folder permissions (roles and users)
   - Delete folders
   - View document count per folder

4. **Document Management**
   - List all documents
   - View document metadata
   - See document status (processing, completed, failed)
   - View folder associations
   - View document owners

## Access Control

### Authentication
- Only authenticated users can access the dashboard
- Only users with `admin` role can view/administer
- Non-admin users are redirected to chat page

### Backend Protection
All admin endpoints are protected with `deps.get_current_admin`:
```python
@router.get("/users")
async def list_users(current_user: User = Depends(deps.get_current_admin)):
    # Only admins can access
```

## API Endpoints

### Statistics
```
GET /api/v1/admin/stats
```
Returns platform-wide statistics.

### User Management
```
GET /api/v1/admin/users          # List all users
POST /api/v1/admin/users          # Create user
PATCH /api/v1/admin/users/{id}     # Update user
DELETE /api/v1/admin/users/{id}    # Delete user
```

### Folder Management
```
GET /api/v1/admin/folders         # List all folders
POST /api/v1/admin/folders         # Create folder (admin only)
```

Note: Folder CRUD operations are also available via `/api/v1/folders/` endpoints, but admin endpoints provide unrestricted access.

### Document Management
```
GET /api/v1/admin/documents       # List all documents
```

## Frontend Components

### Admin Page
**Location**: `frontend/src/app/admin/page.tsx`

**Features**:
- Tabbed interface (Stats, Users, Folders, Documents)
- Real-time data loading
- Inline editing for user names
- Permission management dialogs
- Confirmation dialogs for destructive actions

**Tabs**:
1. **Statistics**: Overview of platform metrics
2. **Users**: User management and role assignment
3. **Folders**: Folder management and permissions
4. **Documents**: Document listing and status

## Usage

### Accessing the Dashboard

1. Log in as an admin user
2. Navigate to `/admin` route
3. Dashboard loads automatically

### Managing Users

1. **Create User**:
   - Click "Create User" button
   - Enter email, name, and role
   - Click "Create User"

2. **Update Role**:
   - Select new role from dropdown in user table
   - Change is saved automatically

3. **Update Name**:
   - Click on name field
   - Edit inline
   - Click outside to save

4. **Delete User**:
   - Click trash icon
   - Confirm deletion
   - User is removed from system

### Managing Folders

1. **Create Folder**:
   - Click "Create Folder" button
   - Enter folder name
   - Optionally select parent folder
   - Click "Create Folder"

2. **Edit Permissions**:
   - Click settings icon on folder row
   - Check/uncheck allowed roles
   - Check/uncheck allowed users
   - Click "Save Permissions"

3. **Delete Folder**:
   - Click trash icon
   - Confirm deletion
   - Folder is deleted (must be empty)

### Viewing Documents

1. Navigate to "Documents" tab
2. View all documents in system
3. See document status, owner, folder, and type
4. Documents are sorted by creation date (newest first)

## Statistics Breakdown

### Documents by Status
- `processing`: Documents being ingested
- `completed`: Documents ready for use
- `failed`: Documents with processing errors

### Users by Role
- `admin`: Full system access
- `manager`: Team management access
- `user`: Standard user access

## Security Considerations

1. **Role Verification**:
   - Frontend checks user role before rendering
   - Backend enforces admin-only access
   - Non-admin requests return 403

2. **Data Protection**:
   - All API calls require authentication
   - Admin endpoints use service role for unrestricted access
   - User deletion prevents self-deletion

3. **Permission Management**:
   - Folder permissions can be edited by admins
   - Changes take effect immediately
   - Permission changes are logged

## Error Handling

### Access Denied
- Non-admin users see "Access denied" message
- Automatic redirect to chat page
- Error logged in console

### API Errors
- Failed operations show alert messages
- Error details logged to console
- User-friendly error messages displayed

## Future Enhancements

1. **Advanced Analytics**:
   - Usage statistics per user
   - Document upload trends
   - Conversation analytics
   - Storage usage metrics

2. **Bulk Operations**:
   - Bulk user role updates
   - Bulk folder permission updates
   - Bulk document operations

3. **Audit Logging**:
   - Track admin actions
   - View change history
   - Export audit logs

4. **User Activity**:
   - View user login history
   - Track document access
   - Monitor conversation activity

5. **System Settings**:
   - Configure platform settings
   - Manage feature flags
   - System health monitoring

## Testing

### Manual Testing

1. **Access Control**:
   - Try accessing as non-admin (should redirect)
   - Verify admin can access all tabs
   - Check API returns 403 for non-admins

2. **User Management**:
   - Create a new user
   - Update user role
   - Delete a user
   - Verify changes persist

3. **Folder Management**:
   - Create a folder
   - Edit folder permissions
   - Delete a folder
   - Verify folder appears in vault

4. **Document Viewing**:
   - Verify all documents are listed
   - Check document statuses
   - Verify folder associations

## Troubleshooting

### Dashboard Not Loading
- Check user has admin role
- Verify authentication token
- Check browser console for errors
- Verify backend is running

### Cannot Create/Update Users
- Verify admin role
- Check email format
- Verify user doesn't already exist
- Check backend logs

### Permissions Not Saving
- Verify folder exists
- Check permission format
- Verify admin access
- Check network requests

---

**Status**: ✅ Implemented and Ready
**Last Updated**: 2024-12-XX

