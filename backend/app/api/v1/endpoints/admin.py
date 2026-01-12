from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID
from app.api import deps
from app.models.user import User, AppRole
from app.db.supabase import get_supabase_client

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: AppRole = AppRole.USER

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[AppRole] = None

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[UUID] = None
    allowed_roles: List[AppRole] = []
    allowed_users: List[UUID] = []

@router.get("/users")
async def list_users(current_user: User = Depends(deps.get_current_admin)):
    """
    List all users (admin only).
    """
    client = get_supabase_client()
    result = client.table("users").select("*").execute()
    return result.data

@router.post("/users")
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(deps.get_current_admin)
):
    """
    Create a new user (admin only).
    Note: In production with Google OAuth, users are auto-created on first login.
    This endpoint is for pre-provisioning or manual user creation.
    """
    client = get_supabase_client()
    
    # Check if user already exists
    existing = client.table("users").select("*").eq("email", user_data.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create user record
    new_user = {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role.value
    }
    
    result = client.table("users").insert(new_user).execute()
    return result.data[0] if result.data else {}

@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(deps.get_current_admin)
):
    """
    Update user role or details (admin only).
    """
    client = get_supabase_client()
    
    update_data = {}
    if user_data.full_name is not None:
        update_data["full_name"] = user_data.full_name
    if user_data.role is not None:
        update_data["role"] = user_data.role.value
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = client.table("users").update(update_data).eq("id", str(user_id)).execute()
    return result.data[0] if result.data else {}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(deps.get_current_admin)
):
    """
    Delete a user (admin only).
    """
    if str(user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    client = get_supabase_client()
    result = client.table("users").delete().eq("id", str(user_id)).execute()
    return {"message": "User deleted successfully"}

@router.get("/folders")
async def list_folders(current_user: User = Depends(deps.get_current_admin)):
    """
    List all folders (admin only).
    """
    client = get_supabase_client()
    result = client.table("folders").select("*").execute()
    return result.data

@router.post("/folders")
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(deps.get_current_admin)
):
    """
    Create a new folder with permissions (admin only).
    """
    client = get_supabase_client()
    
    new_folder = {
        "name": folder_data.name,
        "parent_id": str(folder_data.parent_id) if folder_data.parent_id else None,
        "owner_id": str(current_user.id),
        "allowed_roles": [role.value for role in folder_data.allowed_roles],
        "allowed_users": [str(uid) for uid in folder_data.allowed_users]
    }
    
    result = client.table("folders").insert(new_folder).execute()
    return result.data[0] if result.data else {}

@router.get("/stats")
async def get_stats(current_user: User = Depends(deps.get_current_admin)):
    """
    Get platform statistics (admin only).
    """
    client = get_supabase_client()
    
    users_count = len(client.table("users").select("id").execute().data)
    docs_count = len(client.table("documents").select("id").execute().data)
    convs_count = len(client.table("conversations").select("id").execute().data)
    folders_count = len(client.table("folders").select("id").execute().data)
    
    # Get documents by status
    docs_by_status = {}
    all_docs = client.table("documents").select("status").execute()
    for doc in all_docs.data:
        status = doc.get("status", "processing")
        docs_by_status[status] = docs_by_status.get(status, 0) + 1
    
    # Get users by role
    users_by_role = {}
    all_users = client.table("users").select("role").execute()
    for user in all_users.data:
        role = user.get("role", "user")
        users_by_role[role] = users_by_role.get(role, 0) + 1
    
    return {
        "total_users": users_count,
        "total_documents": docs_count,
        "total_conversations": convs_count,
        "total_folders": folders_count,
        "documents_by_status": docs_by_status,
        "users_by_role": users_by_role
    }

@router.get("/documents")
async def list_all_documents(current_user: User = Depends(deps.get_current_admin)):
    """
    List all documents in the system (admin only).
    """
    client = get_supabase_client()
    result = client.table("documents").select("*").order("created_at", desc=True).execute()
    return result.data
