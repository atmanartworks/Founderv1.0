from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from app.api import deps
from app.models.user import User
from app.db.supabase import get_supabase_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class CreateVersionRequest(BaseModel):
    document_id: str
    version_notes: Optional[str] = None
    change_summary: Optional[str] = None

class RollbackVersionRequest(BaseModel):
    document_id: str
    target_version_number: int
    rollback_notes: Optional[str] = None

@router.get("/{document_id}/versions")
async def get_version_history(
    document_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get version history for a document.
    """
    client = get_supabase_client()
    
    # Check document access
    doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()
    if not doc_response.data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = doc_response.data
    
    # Check access (simplified - should use has_document_access function)
    if doc["owner_id"] != str(current_user.id) and current_user.role != "admin":
        # Check folder access if document is in folder
        if doc.get("folder_id"):
            folder_response = client.table("folders").select("*").eq("id", doc["folder_id"]).single().execute()
            if folder_response.data:
                folder = folder_response.data
                if (folder["owner_id"] != str(current_user.id) and 
                    current_user.role not in folder.get("allowed_roles", []) and
                    str(current_user.id) not in folder.get("allowed_users", [])):
                    raise HTTPException(status_code=403, detail="You don't have permission to access this document")
        else:
            raise HTTPException(status_code=403, detail="You don't have permission to access this document")
    
    # Get version history using function
    try:
        result = client.rpc(
            "get_document_version_history",
            {"p_document_id": document_id}
        ).execute()
        
        return {
            "document_id": document_id,
            "versions": result.data if result.data else []
        }
    except Exception as e:
        logger.error(f"Error getting version history: {str(e)}")
        # Fallback: manual query
        versions = client.table("documents").select("*").or_(
            f"id.eq.{document_id},parent_version_id.eq.{document_id}"
        ).order("version_number", desc=True).execute()
        
        return {
            "document_id": document_id,
            "versions": versions.data if versions.data else []
        }

@router.post("/{document_id}/versions")
async def create_version(
    document_id: str,
    request: CreateVersionRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new version of a document.
    Note: This endpoint creates a version record. The actual new version should be created
    when uploading a new file or updating document content.
    """
    client = get_supabase_client()
    
    # Get current document
    doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()
    if not doc_response.data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = doc_response.data
    
    # Check permission (owner or admin)
    if doc["owner_id"] != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to create versions of this document")
    
    # Create version using function
    try:
        result = client.rpc(
            "create_document_version",
            {
                "p_document_id": document_id,
                "p_storage_path": doc["storage_path"],
                "p_title": doc["title"],
                "p_mime_type": doc.get("mime_type"),
                "p_metadata": doc.get("metadata", {}),
                "p_created_by": str(current_user.id),
                "p_version_notes": request.version_notes,
                "p_change_summary": request.change_summary
            }
        ).execute()
        
        new_version_id = result.data if isinstance(result.data, str) else result.data[0] if result.data else None
        
        if not new_version_id:
            raise HTTPException(status_code=500, detail="Failed to create version")
        
        return {
            "message": "Version created successfully",
            "version_id": new_version_id,
            "document_id": document_id
        }
    except Exception as e:
        logger.error(f"Error creating version: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create version: {str(e)}")

@router.post("/{document_id}/rollback")
async def rollback_version(
    document_id: str,
    request: RollbackVersionRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Rollback document to a previous version.
    """
    client = get_supabase_client()
    
    # Get current document
    doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()
    if not doc_response.data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = doc_response.data
    
    # Check permission (owner or admin)
    if doc["owner_id"] != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to rollback this document")
    
    # Rollback using function
    try:
        result = client.rpc(
            "rollback_document_version",
            {
                "p_document_id": document_id,
                "p_target_version_number": request.target_version_number,
                "p_rollback_by": str(current_user.id),
                "p_rollback_notes": request.rollback_notes
            }
        ).execute()
        
        new_version_id = result.data if isinstance(result.data, str) else result.data[0] if result.data else None
        
        if not new_version_id:
            raise HTTPException(status_code=500, detail="Failed to rollback version")
        
        return {
            "message": "Document rolled back successfully",
            "version_id": new_version_id,
            "document_id": document_id,
            "target_version": request.target_version_number
        }
    except Exception as e:
        logger.error(f"Error rolling back version: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to rollback: {str(e)}")

@router.get("/{document_id}/versions/{version_number}")
async def get_version_details(
    document_id: str,
    version_number: int,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get details of a specific version.
    """
    client = get_supabase_client()
    
    # Check document access
    doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()
    if not doc_response.data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get version
    version_response = client.table("documents").select("*").or_(
        f"id.eq.{document_id},parent_version_id.eq.{document_id}"
    ).eq("version_number", version_number).single().execute()
    
    if not version_response.data:
        raise HTTPException(status_code=404, detail="Version not found")
    
    version = version_response.data
    
    # Get version history record
    version_history = client.table("document_versions").select("*").eq(
        "document_id", version["id"]
    ).eq("version_number", version_number).single().execute()
    
    return {
        "version": version,
        "history": version_history.data if version_history.data else None
    }

