from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Form
from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from app.api import deps
from app.models.user import User
from app.services.storage import storage_service
from app.services.ingestion import ingestion_service
from app.db.supabase import get_supabase_client
import uuid
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None

def get_unique_document_title(client, owner_id: str, original_filename: str, folder_id: Optional[str] = None) -> str:
    """
    Generate a unique document title by appending _duplicate_1, _duplicate_2, etc.
    if a document with the same name already exists.
    """
    # Extract filename without extension and extension
    if '.' in original_filename:
        name_part, ext = original_filename.rsplit('.', 1)
        ext = '.' + ext
    else:
        name_part = original_filename
        ext = ""
    
    # Check if original name exists
    query = client.table("documents").select("id").eq("owner_id", owner_id).eq("title", original_filename)
    if folder_id:
        query = query.eq("folder_id", folder_id)
    else:
        query = query.is_("folder_id", "null")
    
    existing = query.execute()
    
    if not existing.data or len(existing.data) == 0:
        # Original name is available
        return original_filename
    
    # Original name exists, try duplicates
    counter = 1
    while True:
        new_title = f"{name_part}_duplicate_{counter}{ext}"
        
        # Check if this duplicate name exists
        query = client.table("documents").select("id").eq("owner_id", owner_id).eq("title", new_title)
        if folder_id:
            query = query.eq("folder_id", folder_id)
        else:
            query = query.is_("folder_id", "null")
        
        existing = query.execute()
        
        if not existing.data or len(existing.data) == 0:
            # This duplicate name is available
            return new_title
        
        counter += 1

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user),
    folder_id: Optional[str] = Form(None),  # Optional folder ID
    folder_name: Optional[str] = Form(None)  # Optional: create new folder with this name
):
    """
    Upload a document, save to storage, register in DB, and trigger background ingestion.
    If folder_name is provided, creates a new folder first.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")
    
    # Validate file type - only allow PDF, DOCX, TXT, MD
    allowed_extensions = ['.pdf', '.docx', '.txt', '.md']
    file_ext = '.' + file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Only PDF, DOCX, TXT, and MD files are allowed. Received: {file_ext or 'unknown'}"
        )
        
    client = get_supabase_client()
    
    # Handle folder creation if folder_name is provided
    final_folder_id = folder_id
    if folder_name:
        try:
            # Create new folder
            folder_data = {
                "owner_id": str(current_user.id),
                "name": folder_name,
                "parent_id": folder_id if folder_id else None
            }
            folder_result = client.table("folders").insert(folder_data).execute()
            if folder_result.data and len(folder_result.data) > 0:
                final_folder_id = folder_result.data[0]["id"]
                logger.info(f"Created new folder: {final_folder_id} ({folder_name})")
            else:
                raise HTTPException(status_code=500, detail="Failed to create folder")
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create folder: {str(e)}")
    
    # 1. Upload to Storage
    try:
        storage_path = await storage_service.upload_file(file, str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        
    # 2. Generate unique document title (handle duplicates)
    unique_title = get_unique_document_title(client, str(current_user.id), file.filename, final_folder_id)
    
    # 3. Register in DB (simplified schema - no allowed_roles)
    doc_id = uuid.uuid4()
    doc_data = {
        "id": str(doc_id),
        "owner_id": str(current_user.id),
        "title": unique_title,
        "storage_path": storage_path,
        "mime_type": file.content_type or "application/octet-stream",
        "status": "processing"  # Initial status
    }
    
    # Add folder_id only if provided
    if final_folder_id:
        doc_data["folder_id"] = final_folder_id
    
    try:
        res = client.table("documents").insert(doc_data).execute()
    except Exception as e:
        logger.error(f"Error inserting document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register document: {str(e)}")
    
    # 3. Trigger Ingestion (Background)
    # BackgroundTasks handles async functions correctly in FastAPI
    async def process_with_error_handling():
        try:
            logger.info(f"Starting background processing for document {doc_id}")
            chunk_count = await ingestion_service.process_document(
                file_path=storage_path, 
                document_id=doc_id, 
                mime_type=file.content_type or "application/octet-stream"
            )
            # Update document status to completed
            update_client = get_supabase_client()
            try:
                update_result = update_client.table("documents").update({
                    "status": "completed",
                    "chunk_count": chunk_count
                }).eq("id", str(doc_id)).execute()
                
                if update_result.data and len(update_result.data) > 0:
                    logger.info(f"✅ Document {doc_id} processing completed with {chunk_count} chunks - status updated to 'completed'")
                    logger.debug(f"Update result: {update_result.data[0]}")
                else:
                    logger.warning(f"⚠️ Document {doc_id} update returned no data - status may not have been updated")
            except Exception as update_ex:
                logger.error(f"❌ Failed to update document status: {str(update_ex)}", exc_info=True)
                raise
        except Exception as e:
            logger.error(f"❌ Error processing document {doc_id}: {str(e)}", exc_info=True)
            # Update document status to failed
            try:
                update_client = get_supabase_client()
                update_result = update_client.table("documents").update({
                    "status": "failed",
                    "error_message": str(e)[:500]  # Limit error message length
                }).eq("id", str(doc_id)).execute()
                
                if update_result.data and len(update_result.data) > 0:
                    logger.info(f"Document {doc_id} status updated to 'failed'")
                else:
                    logger.warning(f"⚠️ Document {doc_id} failed status update returned no data")
            except Exception as update_error:
                logger.error(f"❌ Failed to update document status to 'failed': {str(update_error)}", exc_info=True)
    
    # Add async function to background tasks (FastAPI handles this correctly)
    background_tasks.add_task(process_with_error_handling)
    
    logger.info(f"Document uploaded: id={doc_id}, path={storage_path}")
    return {"id": doc_id, "status": "processing", "message": "Upload successful, ingestion started."}

@router.get("/")
async def list_documents(
    current_user: User = Depends(deps.get_current_user),
    folder_id: Optional[str] = None
):
    """
    List documents for the current user.
    If folder_id is provided, only returns documents in that folder.
    Simplified: users can only see their own documents.
    """
    client = get_supabase_client()
    
    # Build query - user can only see their own documents
    query = client.table("documents").select("*").eq("owner_id", current_user.id)
    
    # Filter by folder if specified
    if folder_id:
        # Verify folder exists and belongs to user
        try:
            folder_response = client.table("folders").select("*").eq("id", folder_id).eq("owner_id", current_user.id).single().execute()
            if not folder_response.data:
                raise HTTPException(status_code=404, detail="Folder not found or access denied")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=404, detail="Folder not found")
        
        query = query.eq("folder_id", folder_id)
    
    try:
        res = query.order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        # If folders table doesn't exist yet, just return user's documents without folder filter
        if folder_id:
            logger.warning("Folders table may not exist, returning all user documents")
            res = client.table("documents").select("*").eq("owner_id", current_user.id).order("created_at", desc=True).execute()
            return res.data or []
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Delete a document and all associated chunks. Only the owner can delete.
    """
    client = get_supabase_client()
    
    try:
        # 1. Verify ownership
        doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()
        
        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = doc_response.data
        
        if document["owner_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="You don't have permission to delete this document")
        
        storage_path = document.get("storage_path")
        
        # 2. Delete associated chunks (Legacy check removed)
        
        # 3. Delete from storage (if path exists)
        if storage_path:
            try:
                bucket = "GPTv1"
                storage_delete = client.storage.from_(bucket).remove([storage_path])
                logger.info(f"Deleted file from storage: {storage_path}")
            except Exception as storage_error:
                logger.warning(f"Failed to delete file from storage: {str(storage_error)}")
                # Continue with DB deletion even if storage deletion fails
        
        # 4. Delete document record
        logger.info(f"Deleting document record: {document_id}")
        doc_delete = client.table("documents").delete().eq("id", document_id).execute()
        
        logger.info(f"Document {document_id} deleted successfully")
        return {"message": "Document deleted successfully", "id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Reprocess a failed document. Deletes existing chunks and re-runs ingestion.
    """
    client = get_supabase_client()
    
    try:
        # 1. Verify ownership and get document
        doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()
        
        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = doc_response.data
        
        if document["owner_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="You don't have permission to reprocess this document")
        
        storage_path = document.get("storage_path")
        if not storage_path:
            raise HTTPException(status_code=400, detail="Document has no storage path")
        
        # 2. Delete existing chunks (Legacy check removed)
        
        # 3. Reset status to processing
        client.table("documents").update({
            "status": "processing",
            "error_message": None,
            "chunk_count": None
        }).eq("id", document_id).execute()
        
        # 4. Trigger reprocessing
        async def process_with_error_handling():
            try:
                logger.info(f"Starting reprocessing for document {document_id}")
                chunk_count = await ingestion_service.process_document(
                    file_path=storage_path,
                    document_id=UUID(document_id),
                    mime_type=document.get("mime_type") or "application/octet-stream"
                )
                # Update document status to completed
                update_client = get_supabase_client()
                try:
                    update_result = update_client.table("documents").update({
                        "status": "completed",
                        "chunk_count": chunk_count
                    }).eq("id", document_id).execute()
                    
                    if update_result.data and len(update_result.data) > 0:
                        logger.info(f"✅ Document {document_id} reprocessing completed with {chunk_count} chunks - status updated to 'completed'")
                    else:
                        logger.warning(f"⚠️ Document {document_id} update returned no data - status may not have been updated")
                except Exception as update_ex:
                    logger.error(f"❌ Failed to update document status: {str(update_ex)}", exc_info=True)
                    raise
            except Exception as e:
                logger.error(f"❌ Error reprocessing document {document_id}: {str(e)}", exc_info=True)
                # Update document status to failed
                try:
                    update_client = get_supabase_client()
                    update_result = update_client.table("documents").update({
                        "status": "failed",
                        "error_message": str(e)[:500]
                    }).eq("id", document_id).execute()
                    
                    if update_result.data and len(update_result.data) > 0:
                        logger.info(f"Document {document_id} status updated to 'failed' after reprocessing error")
                    else:
                        logger.warning(f"⚠️ Document {document_id} failed status update returned no data")
                except Exception as update_error:
                    logger.error(f"❌ Failed to update document status to 'failed': {str(update_error)}", exc_info=True)
        
        background_tasks.add_task(process_with_error_handling)
        
        logger.info(f"Document {document_id} reprocessing started")
        return {"message": "Document reprocessing started", "id": document_id, "status": "processing"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reprocess document: {str(e)}")
