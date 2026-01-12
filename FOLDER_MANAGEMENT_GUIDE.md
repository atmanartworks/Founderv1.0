# Folder Management System - Implementation Guide

## Overview

The folder management system provides hierarchical organization of documents with role-based access control. Users can create folders, organize documents, and control who has access to each folder.

## Features

### ✅ Implemented

1. **Hierarchical Folder Structure**
   - Create folders and subfolders
   - Navigate folder tree
   - Visual folder tree with expand/collapse

2. **Permission System**
   - Role-based access (admin, manager, user)
   - User-specific access
   - Owner always has full access
   - Admin has access to all folders

3. **Document Organization**
   - Upload documents to specific folders
   - Filter documents by folder
   - View documents in selected folder
   - Document count per folder

4. **Folder Management**
   - Create folders
   - Delete folders (must be empty)
   - View folder tree
   - Select folder for upload

## Backend API

### Endpoints

#### List Folders
```
GET /api/v1/folders/
GET /api/v1/folders/?parent_id=<folder_id>
```
Returns folders accessible to the current user. If `parent_id` is provided, returns only children of that folder.

#### Get Folder
```
GET /api/v1/folders/{folder_id}
```
Get a specific folder with its children and document count.

#### Create Folder
```
POST /api/v1/folders/
Body: {
  "name": "Folder Name",
  "parent_id": "uuid-optional",
  "allowed_roles": ["admin", "manager"],
  "allowed_users": ["user-uuid-1", "user-uuid-2"]
}
```

#### Update Folder
```
PUT /api/v1/folders/{folder_id}
Body: {
  "name": "New Name",
  "parent_id": "new-parent-id",
  "allowed_roles": [...],
  "allowed_users": [...]
}
```

#### Delete Folder
```
DELETE /api/v1/folders/{folder_id}
```
Deletes folder if it's empty (no documents or subfolders).

#### Get Folder Tree
```
GET /api/v1/folders/tree/all
```
Returns complete hierarchical folder tree structure.

#### List Folder Documents
```
GET /api/v1/folders/{folder_id}/documents
```
Returns all documents in a specific folder.

## Permission Logic

### Access Rules

1. **Owner**: Always has full access (create, read, update, delete)
2. **Admin**: Has access to all folders
3. **Role-based**: If user's role is in `allowed_roles` array
4. **User-specific**: If user's ID is in `allowed_users` array

### Permission Checking

```python
def check_folder_access(folder: dict, user: User) -> bool:
    # Owner always has access
    if folder.get("owner_id") == str(user.id):
        return True
    
    # Admin always has access
    if user.role == "admin":
        return True
    
    # Check allowed roles
    if user.role in folder.get("allowed_roles", []):
        return True
    
    # Check allowed users
    if str(user.id) in folder.get("allowed_users", []):
        return True
    
    return False
```

## Frontend Components

### FolderTree Component

**Location**: `frontend/src/components/FolderTree.tsx`

**Features**:
- Hierarchical folder display
- Expand/collapse folders
- Create new folders
- Delete folders
- Select folder for filtering
- Document count display

**Props**:
```typescript
interface FolderTreeProps {
    selectedFolderId: string | null;
    onSelectFolder: (folderId: string | null) => void;
    onFolderChange: () => void;
    onFolderListChange?: (folders: any[]) => void;
}
```

### Vault Page Integration

**Location**: `frontend/src/app/vault/page.tsx`

**Features**:
- Folder sidebar with tree view
- Filter documents by folder
- Upload documents to folders
- Folder selection in upload dialog

## Usage

### Creating a Folder

1. Click "New" button in folder sidebar
2. Enter folder name
3. Optionally select parent folder
4. Click "Create"

### Organizing Documents

1. **Upload to Folder**:
   - Click "Upload Document"
   - Select file
   - Choose folder from dropdown (optional)
   - Click "Upload"

2. **View Folder Contents**:
   - Click on folder in sidebar
   - Documents in that folder are displayed
   - Click "All Documents" to see all

3. **Move Documents** (Future):
   - Currently documents are assigned at upload
   - Move functionality can be added later

### Managing Permissions

**For Admins**:
- Can access all folders
- Can update any folder's permissions
- Can delete any folder

**For Folder Owners**:
- Can update folder name
- Can update permissions
- Can delete folder (if empty)

**For Users with Access**:
- Can view folder contents
- Can upload to folder (if they have write access)
- Cannot modify folder settings

## Database Schema

```sql
create table public.folders (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  parent_id uuid references public.folders(id),
  owner_id uuid references public.users(id),
  
  -- Permissions
  allowed_roles app_role[] default '{}',
  allowed_users uuid[] default '{}',
  
  created_at timestamptz default now()
);
```

## Integration with Documents

Documents reference folders via `folder_id`:

```sql
create table public.documents (
  ...
  folder_id uuid references public.folders(id),
  ...
);
```

When listing documents:
- If `folder_id` is provided, only documents in that folder are returned
- Permission check ensures user has access to the folder
- Documents without folders are shown in "All Documents"

## Security Considerations

1. **Permission Enforcement**:
   - All folder operations check permissions
   - Document listing respects folder permissions
   - Vector search respects folder permissions

2. **Validation**:
   - Cannot delete folder with documents
   - Cannot delete folder with subfolders
   - Cannot set folder as its own parent (circular reference)

3. **Default Permissions**:
   - New folders are accessible only to owner by default
   - Admins can grant access to roles/users
   - Users can grant access to themselves

## Future Enhancements

1. **Move Documents**: Move documents between folders
2. **Bulk Operations**: Move/delete multiple documents
3. **Folder Templates**: Pre-configured folder structures
4. **Folder Sharing**: Share folders with specific users
5. **Folder Search**: Search folders by name
6. **Folder Metadata**: Add descriptions, tags, etc.

## Testing

### Manual Testing

1. **Create Folder**:
   - Create a root folder
   - Create a subfolder
   - Verify hierarchy displays correctly

2. **Upload to Folder**:
   - Upload document to root
   - Upload document to subfolder
   - Verify documents appear in correct folders

3. **Permission Testing**:
   - Create folder as user A
   - Try to access as user B (should fail)
   - Grant access to user B
   - Verify user B can now access

4. **Delete Folder**:
   - Try to delete folder with documents (should fail)
   - Delete all documents
   - Delete folder (should succeed)

## Troubleshooting

### Folders Not Showing

- Check user has access to folders
- Verify folder API endpoint is working
- Check browser console for errors

### Cannot Upload to Folder

- Verify folder exists
- Check user has access to folder
- Verify `folder_id` is being sent in upload request

### Permission Denied

- Check folder permissions in database
- Verify user role matches `allowed_roles`
- Check user ID is in `allowed_users`

---

**Status**: ✅ Implemented and Ready
**Last Updated**: 2024-12-XX

