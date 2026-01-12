from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from app.api import deps
from app.models.user import User
from app.db.supabase import get_supabase_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    allowed_roles: Optional[List[str]] = []
    allowed_users: Optional[List[str]] = []

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    allowed_roles: Optional[List[str]] = None
    allowed_users: Optional[List[str]] = None

def check_folder_access(folder: dict, user: User) -> bool:
    """
    Check if user has access to a folder based on permissions.
    """
    # Owner always has access
    if folder.get("owner_id") == str(user.id):
        return True
    
    # Admin always has access
    if user.role == "admin":
        return True
    
    # Check allowed roles
    allowed_roles = folder.get("allowed_roles", [])
    if user.role in allowed_roles:
        return True
    
    # Check allowed users
    allowed_users = folder.get("allowed_users", [])
    if str(user.id) in allowed_users:
        return True
    
    return False

def get_accessible_folder_ids(client, user: User) -> List[str]:
    """
    Get all folder IDs the user has access to.
    """
    # Get all folders
    all_folders = client.table("folders").select("*").execute()
    
    accessible_ids = []
    for folder in all_folders.data:
        if check_folder_access(folder, user):
            accessible_ids.append(folder["id"])
    
    return accessible_ids

@router.get("/")
async def list_folders(
    current_user: User = Depends(deps.get_current_user),
    parent_id: Optional[str] = None
):
    """
    List folders accessible to the current user.
    If parent_id is provided, returns only children of that folder.
    """
    client = get_supabase_client()
    
    # Get accessible folder IDs
    accessible_ids = get_accessible_folder_ids(client, current_user)
    
    if not accessible_ids:
        return []
    
    # Query folders
    query = client.table("folders").select("*").in_("id", accessible_ids)
    
    if parent_id:
        query = query.eq("parent_id", parent_id)
    else:
        # Only root folders (no parent)
        query = query.is_("parent_id", "null")
    
    result = query.order("name").execute()
    
    # Add document count for each folder
    folders_with_counts = []
    for folder in result.data:
        doc_count = client.table("documents").select("id", count="exact").eq("folder_id", folder["id"]).execute()
        folder["document_count"] = doc_count.count if doc_count.count else 0
        folders_with_counts.append(folder)
    
    return folders_with_counts

@router.get("/{folder_id}")
async def get_folder(
    folder_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get a specific folder by ID (if user has access).
    """
    client = get_supabase_client()
    
    folder_response = client.table("folders").select("*").eq("id", folder_id).single().execute()
    
    if not folder_response.data:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder = folder_response.data
    
    # Check access
    if not check_folder_access(folder, current_user):
        raise HTTPException(status_code=403, detail="You don't have permission to access this folder")
    
    # Get document count
    doc_count = client.table("documents").select("id", count="exact").eq("folder_id", folder_id).execute()
    folder["document_count"] = doc_count.count if doc_count.count else 0
    
    # Get children folders
    children = client.table("folders").select("*").eq("parent_id", folder_id).order("name").execute()
    folder["children"] = children.data
    
    return folder

@router.post("/")
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new folder. Users can create folders, but permissions are restricted.
    """
    client = get_supabase_client()
    
    # Validate parent folder if provided
    if folder_data.parent_id:
        parent_response = client.table("folders").select("*").eq("id", folder_data.parent_id).single().execute()
        if not parent_response.data:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        
        # Check access to parent
        if not check_folder_access(parent_response.data, current_user):
            raise HTTPException(status_code=403, detail="You don't have permission to create folders in this parent")
    
    # Set default permissions based on user role
    allowed_roles = folder_data.allowed_roles if folder_data.allowed_roles else []
    allowed_users = folder_data.allowed_users if folder_data.allowed_users else []
    
    # If user is not admin, they can only grant access to themselves by default
    if current_user.role != "admin" and not allowed_users:
        allowed_users = [str(current_user.id)]
    
    new_folder = {
        "name": folder_data.name,
        "parent_id": folder_data.parent_id,
        "owner_id": str(current_user.id),
        "allowed_roles": allowed_roles,
        "allowed_users": allowed_users
    }
    
    result = client.table("folders").insert(new_folder).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create folder")
    
    return result.data[0]

@router.put("/{folder_id}")
async def update_folder(
    folder_id: str,
    folder_data: FolderUpdate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Update a folder. Only owner or admin can update.
    """
    client = get_supabase_client()
    
    # Get existing folder
    folder_response = client.table("folders").select("*").eq("id", folder_id).single().execute()
    
    if not folder_response.data:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder = folder_response.data
    
    # Check permission (owner or admin only)
    if folder["owner_id"] != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to update this folder")
    
    # Validate parent if changing
    if folder_data.parent_id is not None and folder_data.parent_id != folder.get("parent_id"):
        if folder_data.parent_id:
            parent_response = client.table("folders").select("*").eq("id", folder_data.parent_id).single().execute()
            if not parent_response.data:
                raise HTTPException(status_code=404, detail="Parent folder not found")
            
            # Prevent circular references
            if folder_data.parent_id == folder_id:
                raise HTTPException(status_code=400, detail="Cannot set folder as its own parent")
    
    # Build update data
    update_data = {}
    if folder_data.name is not None:
        update_data["name"] = folder_data.name
    if folder_data.parent_id is not None:
        update_data["parent_id"] = folder_data.parent_id
    if folder_data.allowed_roles is not None:
        update_data["allowed_roles"] = folder_data.allowed_roles
    if folder_data.allowed_users is not None:
        update_data["allowed_users"] = folder_data.allowed_users
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = client.table("folders").update(update_data).eq("id", folder_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update folder")
    
    return result.data[0]

async def _delete_folder_recursive(
    folder_id: str,
    current_user: User,
    client
) -> dict:
    """
    Helper function to recursively delete a folder and all its contents.
    Returns dict with deletion statistics.
    """
    # Get folder
    folder_response = client.table("folders").select("*").eq("id", folder_id).single().execute()
    if not folder_response.data:
        return {"deleted_documents": 0, "deleted_subfolders": 0}
    
    folder = folder_response.data
    
    # Verify ownership
    if folder["owner_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this folder")
    
    deleted_docs_count = 0
    deleted_subfolders_count = 0
    
    # 1. Recursively delete all subfolders first
    subfolders = client.table("folders").select("*").eq("parent_id", folder_id).execute()
    for subfolder in subfolders.data or []:
        subfolder_result = await _delete_folder_recursive(subfolder["id"], current_user, client)
        deleted_docs_count += subfolder_result["deleted_documents"]
        deleted_subfolders_count += 1 + subfolder_result["deleted_subfolders"]  # +1 for the subfolder itself
    
    # 2. Delete all documents in this folder
    documents = client.table("documents").select("*").eq("folder_id", folder_id).execute()
    
    for doc in documents.data or []:
        try:
            # Verify ownership
            if doc["owner_id"] != str(current_user.id):
                logger.warning(f"Skipping document {doc['id']} - not owned by user")
                continue
            
            doc_id = doc["id"]
            storage_path = doc.get("storage_path")
            
            # Delete associated chunks
            # Delete from storage
            if storage_path:
                try:
                    storage_delete = client.storage.from_("GPTv1").remove([storage_path])
                except Exception as e:
                    logger.error(f"Error deleting file from storage: {e}")
            
            # Delete document record (cascading delete should handle chunks if we had FKs, but we don't have chunks table anymore)
            client.table("documents").delete().eq("id", doc_id).execute()
            deleted_docs_count += 1
            logger.info(f"Deleted document {doc_id}")
            
        except Exception as doc_error:
            logger.error(f"Error deleting document {doc.get('id')}: {str(doc_error)}", exc_info=True)
            # Continue with other documents even if one fails
    
    # 3. Delete the folder itself
    client.table("folders").delete().eq("id", folder_id).execute()
    logger.info(f"Deleted folder {folder_id}")
    
    return {
        "deleted_documents": deleted_docs_count,
        "deleted_subfolders": deleted_subfolders_count
    }

@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Delete a folder and all its contents.
    - Deletes all documents in the folder (and their chunks, storage files)
    - Recursively deletes all subfolders and their contents
    - Only owner can delete (simplified for single-user system)
    """
    client = get_supabase_client()
    
    # Verify folder exists
    folder_response = client.table("folders").select("*").eq("id", folder_id).single().execute()
    if not folder_response.data:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder = folder_response.data
    
    # Check permission (owner only - simplified for single-user system)
    if folder["owner_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this folder")
    
    try:
        # Recursively delete folder and all contents
        result = await _delete_folder_recursive(folder_id, current_user, client)
        
        logger.info(f"Folder {folder_id} deleted by user {current_user.id}. Deleted {result['deleted_documents']} documents and {result['deleted_subfolders']} subfolders")
        
        return {
            "message": "Folder and all contents deleted successfully",
            "id": folder_id,
            "deleted_documents": result["deleted_documents"],
            "deleted_subfolders": result["deleted_subfolders"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting folder {folder_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete folder: {str(e)}")

@router.get("/{folder_id}/documents")
async def list_folder_documents(
    folder_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    List all documents in a folder (if user has access).
    """
    client = get_supabase_client()
    
    # Check folder access
    folder_response = client.table("folders").select("*").eq("id", folder_id).single().execute()
    
    if not folder_response.data:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    if not check_folder_access(folder_response.data, current_user):
        raise HTTPException(status_code=403, detail="You don't have permission to access this folder")
    
    # Get documents in folder
    result = client.table("documents").select("*").eq("folder_id", folder_id).order("created_at", desc=True).execute()
    
    return result.data

@router.get("/tree/all")
async def get_folder_tree(
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get complete folder tree structure (only accessible folders).
    """
    client = get_supabase_client()
    
    # Get all accessible folders
    accessible_ids = get_accessible_folder_ids(client, current_user)
    
    if not accessible_ids:
        return []
    
    all_folders = client.table("folders").select("*").in_("id", accessible_ids).order("name").execute()
    
    # Build tree structure
    folder_map = {folder["id"]: {**folder, "children": []} for folder in all_folders.data}
    root_folders = []
    
    for folder in all_folders.data:
        folder_obj = folder_map[folder["id"]]
        
        # Get document count
        doc_count = client.table("documents").select("id", count="exact").eq("folder_id", folder["id"]).execute()
        folder_obj["document_count"] = doc_count.count if doc_count.count else 0
        
        if folder.get("parent_id"):
            parent_id = folder["parent_id"]
            if parent_id in folder_map:
                folder_map[parent_id]["children"].append(folder_obj)
        else:
            root_folders.append(folder_obj)
    
    return root_folders

