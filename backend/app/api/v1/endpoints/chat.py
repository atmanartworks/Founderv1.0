from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
from uuid import UUID
from openai import OpenAI
from app.api import deps
from app.models.user import User
from app.core.config import settings
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    FileUploadError,
    DatabaseError
)
from app.db.supabase import get_supabase_client
from app.services.document_generator import document_generator
from app.services.storage import StorageService
from app.services.ingestion import ingestion_service
import json
import re
import asyncio
import logging
import uuid

router = APIRouter()
client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)

def get_unique_document_title(db, owner_id: str, original_filename: str, folder_id: Optional[str] = None) -> str:
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
    query = db.table("documents").select("id").eq("owner_id", owner_id).eq("title", original_filename)
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
        query = db.table("documents").select("id").eq("owner_id", owner_id).eq("title", new_title)
        if folder_id:
            query = query.eq("folder_id", folder_id)
        else:
            query = query.is_("folder_id", "null")
        
        existing = query.execute()
        
        if not existing.data or len(existing.data) == 0:
            # This duplicate name is available
            return new_title
        
        counter += 1

class ChatQueryRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    stream: bool = False  # Enable streaming
    file_upload: Optional[str] = None  # File ID if file was uploaded

class ConversationCreate(BaseModel):
    title: str

@router.post("/upload-file")
async def upload_file_in_chat(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    current_user: User = Depends(deps.get_current_user),
    conversation_id: Optional[str] = None
):
    """
    Upload a file directly from chat interface.
    File will be processed and appear in document vault.
    Returns document info for immediate use in chat.
    """
    if not file.filename:
        raise ValidationError("Filename is required", field="file")
    
    # Validate file type - only allow PDF, DOCX, TXT, MD
    allowed_extensions = ['.pdf', '.docx', '.txt', '.md']
    file_ext = '.' + file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise FileUploadError(
            f"Invalid file type. Only PDF, DOCX, TXT, and MD files are allowed",
            reason=f"Received: {file_ext or 'unknown'}"
        )
    
    db = get_supabase_client()
    storage_service = StorageService()
    
    try:
        # 1. Upload to Storage
        storage_path = await storage_service.upload_file(file, str(current_user.id))
        
        # 2. Generate unique document title (handle duplicates)
        unique_title = get_unique_document_title(db, str(current_user.id), file.filename, folder_id)
        
        # 3. Register in DB
        doc_id = uuid.uuid4()
        doc_data = {
            "id": str(doc_id),
            "owner_id": str(current_user.id),
            "title": unique_title,
            "storage_path": storage_path,
            "mime_type": file.content_type or "application/octet-stream",
            "status": "processing"
        }
        
        # Add folder_id if provided
        if folder_id:
            doc_data["folder_id"] = folder_id
        
        res = db.table("documents").insert(doc_data).execute()
        
        # 3. Trigger background ingestion
        async def process_document():
            try:
                logger.info(f"Processing uploaded file from chat: {doc_id}")
                chunk_count = await ingestion_service.process_document(
                    file_path=storage_path,
                    document_id=doc_id,
                    mime_type=file.content_type or "application/octet-stream"
                )
                # Get fresh client for update
                update_db = get_supabase_client()
                try:
                    update_result = update_db.table("documents").update({
                        "status": "completed",
                        "chunk_count": chunk_count
                    }).eq("id", str(doc_id)).execute()
                    
                    if update_result.data and len(update_result.data) > 0:
                        logger.info(f"✅ File from chat processed: {doc_id} with {chunk_count} chunks - status updated to 'completed'")
                        logger.debug(f"Update result: {update_result.data[0]}")
                    else:
                        logger.warning(f"⚠️ Document {doc_id} update returned no data - status may not have been updated")
                except Exception as update_ex:
                    logger.error(f"❌ Failed to update document status: {str(update_ex)}", exc_info=True)
                    raise
            except Exception as e:
                logger.error(f"❌ Error processing file from chat: {str(e)}", exc_info=True)
                try:
                    update_db = get_supabase_client()
                    update_result = update_db.table("documents").update({
                        "status": "failed",
                        "error_message": str(e)[:500]  # Limit error message length
                    }).eq("id", str(doc_id)).execute()
                    
                    if update_result.data and len(update_result.data) > 0:
                        logger.info(f"Document {doc_id} status updated to 'failed'")
                    else:
                        logger.warning(f"⚠️ Document {doc_id} failed status update returned no data")
                except Exception as update_error:
                    logger.error(f"❌ Failed to update document status to 'failed': {str(update_error)}", exc_info=True)
        
        background_tasks.add_task(process_document)
        
        # 4. Return document info
        # 4. Return document info
        response_data = {
            "document_id": str(doc_id),
            "title": file.filename,
            "status": "processing",
            "message": f"File '{file.filename}' uploaded successfully. It's being processed and will be available shortly."
        }

        # 5. Persist to chat history if conversation_id provided
        if conversation_id:
            try:
                # Save user message
                db.table("messages").insert({
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": f"Uploaded: {file.filename}",
                    "uploaded_document": {
                        "id": str(doc_id),
                        "title": file.filename,
                        "status": "processing"
                    }
                }).execute()
                
                # Save assistant message
                db.table("messages").insert({
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": response_data["message"],
                    "citations": []
                }).execute()
                logger.info(f"Persisted upload messages for conversation {conversation_id}")
            except Exception as msg_error:
                logger.error(f"Failed to persist chat messages for upload: {msg_error}")
                # Don't fail the upload just because message logging failed
        
        return response_data
        
    except FileUploadError:
        raise
    except Exception as e:
        logger.error(f"Error uploading file in chat: {str(e)}", exc_info=True)
        raise FileUploadError("File upload failed", reason=str(e))


@router.post("/query")
async def chat_query(
    request: ChatQueryRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Chat query endpoint with optional streaming support.
    If stream=true, returns Server-Sent Events (SSE) stream.
    Otherwise, returns complete response.
    """
    # If streaming is requested, return streaming response
    if request.stream and settings.ENABLE_STREAMING:
        return StreamingResponse(
            stream_chat_response(request, current_user),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Expose-Headers": "*"
            }
        )
    
    # Non-streaming flow (existing code)
    return await chat_query_non_streaming(request, current_user)

async def chat_query_non_streaming(
    request: ChatQueryRequest,
    current_user: User
):
    """
    Non-streaming chat query handler.
    """
    db = get_supabase_client()
    
    # Check if user is requesting document generation
    generation_keywords = [
        "generate", "create", "make", "write", "draft",
        "document", "report", "proposal", "summary"
    ]
    
    query_lower = request.query.lower()
    is_generation_request = any(
        keyword in query_lower for keyword in generation_keywords
    ) and ("document" in query_lower or "report" in query_lower or 
           "proposal" in query_lower or "summary" in query_lower)
    
    if is_generation_request:
        # Extract topic from query
        topic = request.query
        
        # Determine document type
        doc_type = "report"
        if "summary" in query_lower:
            doc_type = "summary"
        elif "proposal" in query_lower:
            doc_type = "proposal"
        elif "analysis" in query_lower:
            doc_type = "analysis"
        
        try:
            # Generate document content with GPT-4
            system_prompt = f"""You are a professional document writer. Generate a well-structured {doc_type} 
based on the user's request. Use clear headings, bullet points where appropriate, and maintain a professional tone.
Format the output in plain text with clear section breaks using double newlines."""

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.query}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            title = f"{doc_type.title()}: {topic[:50]}"

            # Generate PDF
            pdf_buffer = document_generator.generate_pdf(content, title)
            
            # Upload to storage
            storage_service = StorageService()
            pdf_filename = f"{doc_type}_{topic[:30].replace(' ', '_')}.pdf"
            
            pdf_path = await storage_service.upload_file_from_buffer(
                pdf_buffer,
                pdf_filename,
                "application/pdf",
                str(current_user.id),
                folder_prefix="generated"
            )
            
            # Save to documents table
            doc_data = {
                "owner_id": str(current_user.id),
                "title": f"{title} (PDF)",
                "storage_path": pdf_path,
                "mime_type": "application/pdf",
                "metadata": {
                    "generated": True,
                    "document_type": doc_type,
                    "topic": topic
                }
            }
            pdf_doc = db.table("documents").insert(doc_data).execute()
            doc_id = pdf_doc.data[0]["id"] if pdf_doc.data else None
            
            # Create download URL
            download_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/GPTv1/{pdf_path}"
            
            # Return response with download link
            answer = f"""I've generated a {doc_type} for you: "{title}"

📄 **{pdf_filename}**

The document has been created with a watermark and saved to your vault. You can download it using the link below or find it in the Document Vault.

[Download PDF]({download_url})

The document includes:
{content[:200]}...

Would you like me to make any changes or generate it in a different format?"""

            # Save to conversation
            if request.conversation_id:
                # Save user message
                db.table("messages").insert({
                    "conversation_id": request.conversation_id,
                    "role": "user",
                    "content": request.query
                }).execute()
                
                # Save assistant message
                db.table("messages").insert({
                    "conversation_id": request.conversation_id,
                    "role": "assistant",
                    "content": answer,
                    "citations": json.dumps([{
                        "document_id": doc_id,
                        "document_title": title,
                        "label": "[Generated]",
                        "download_url": download_url
                    }])
                }).execute()

            return {
                "answer": answer,
                "citations": [{
                    "document_id": doc_id,
                    "document_title": title,
                    "label": "[Download]",
                    "download_url": download_url,
                    "metadata": {"storage_path": pdf_path}
                }],
                "generated_document": {
                    "id": doc_id,
                    "filename": pdf_filename,
                    "download_url": download_url
                }
            }
            
        except Exception as e:
            print(f"Document generation error: {e}")
            # Fall through to normal RAG if generation fails
    
    # Normal RAG flow (existing code)
    from app.services.chat import chat_service
    
    try:
        conversation_uuid = None
        if request.conversation_id:
            try:
                conversation_uuid = UUID(request.conversation_id)
            except ValueError:
                conversation_uuid = None
        
        result = await chat_service.generate_response(
            query=request.query,
            user=current_user,
            conversation_id=conversation_uuid
        )
        return result
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def stream_chat_response(
    request: ChatQueryRequest,
    current_user: User
) -> AsyncGenerator[str, None]:
    """
    Stream chat response using Server-Sent Events (SSE).
    """
    from app.services.chat import chat_service
    
    # CRITICAL: Yield immediately to establish connection and send CORS headers
    # This must be the FIRST thing we do, before any other operations
    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    try:
        conversation_uuid = None
        if request.conversation_id:
            try:
                conversation_uuid = UUID(request.conversation_id)
            except ValueError:
                conversation_uuid = None
        
        # Log for debugging
        logger.info(f"Starting streaming response for user {current_user.id}, query: {request.query[:50]}...")
        
        # Track if we've yielded anything from the service
        has_yielded_from_service = False
        
        try:
            async for chunk in chat_service.generate_response_stream(
                query=request.query,
                user=current_user,
                conversation_id=conversation_uuid
            ):
                has_yielded_from_service = True
                yield chunk
                await asyncio.sleep(0)  # Yield control to event loop
            
            # If we never yielded anything from service, send an error
            if not has_yielded_from_service:
                logger.warning("Stream completed without yielding any chunks from service")
                yield f"data: {json.dumps({'type': 'error', 'content': 'No response generated. Please try again.'})}\n\n"
                
        except Exception as stream_error:
            logger.error(f"Error in stream generator: {str(stream_error)}", exc_info=True)
            # Always try to yield error message
            try:
                yield f"data: {json.dumps({'type': 'error', 'content': f'Error: {str(stream_error)}'})}\n\n"
            except Exception as yield_error:
                logger.error(f"Failed to yield error message: {yield_error}")
            
    except HTTPException as e:
        # HTTP exceptions (like 401) - send as error message
        logger.error(f"HTTP error in streaming: {e.status_code} - {e.detail}")
        try:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error {e.status_code}: {e.detail}'})}\n\n"
        except Exception as yield_error:
            logger.error(f"Failed to yield HTTP error: {yield_error}")
    except Exception as e:
        logger.error(f"Streaming chat error: {str(e)}", exc_info=True)
        try:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error: {str(e)}'})}\n\n"
        except Exception as yield_error:
            logger.error(f"Failed to yield error: {yield_error}")

@router.post("/conversations")
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(deps.get_current_user)
):
    db = get_supabase_client()
    conv = db.table("conversations").insert({
        "user_id": str(current_user.id),
        "title": request.title
    }).execute()
    return conv.data[0] if conv.data else {}

@router.get("/conversations")
async def list_conversations(current_user: User = Depends(deps.get_current_user)):
    db = get_supabase_client()
    convs = db.table("conversations").select("*").eq("user_id", str(current_user.id)).order("created_at", desc=True).execute()
    return convs.data

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: ConversationCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Update a conversation title.
    Only the owner can update.
    """
    db = get_supabase_client()
    
    try:
        # Verify ownership
        conv_response = db.table("conversations").select("*").eq("id", conversation_id).single().execute()
        
        if not conv_response.data:
            raise NotFoundError("Conversation", conversation_id)
        
        conversation = conv_response.data
        
        if conversation["user_id"] != str(current_user.id):
            raise AuthorizationError("You don't have permission to update this conversation")
        
        # Update conversation title
        update_response = db.table("conversations").update({
            "title": request.title
        }).eq("id", conversation_id).execute()
        
        if not update_response.data:
            raise DatabaseError("Failed to update conversation", operation="update")
        
        logger.info(f"Conversation {conversation_id} title updated to: {request.title}")
        return update_response.data[0] if update_response.data else {}
        
    except (NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_id}: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to update conversation", operation="update")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Delete a conversation and all its messages.
    Only the owner can delete.
    """
    db = get_supabase_client()
    
    try:
        # Verify ownership
        conv_response = db.table("conversations").select("*").eq("id", conversation_id).single().execute()
        
        if not conv_response.data:
            raise NotFoundError("Conversation", conversation_id)
        
        conversation = conv_response.data
        
        if conversation["user_id"] != str(current_user.id):
            raise AuthorizationError("You don't have permission to delete this conversation")
        
        # Delete all messages first
        logger.info(f"Deleting messages for conversation {conversation_id}")
        messages_delete = db.table("messages").delete().eq("conversation_id", conversation_id).execute()
        logger.info(f"Deleted {len(messages_delete.data) if messages_delete.data else 0} messages")
        
        # Delete conversation
        db.table("conversations").delete().eq("id", conversation_id).execute()
        
        logger.info(f"Conversation {conversation_id} deleted successfully")
        return {"message": "Conversation deleted successfully", "id": conversation_id}
        
    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to delete conversation", operation="delete")

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get all messages for a conversation.
    Only returns messages for conversations owned by the current user.
    """
    db = get_supabase_client()
    
    # Verify conversation belongs to user
    try:
        conv = db.table("conversations").select("*").eq("id", conversation_id).eq("user_id", str(current_user.id)).single().execute()
        if not conv.data:
            raise NotFoundError("Conversation", conversation_id)
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation: {str(e)}", exc_info=True)
        raise NotFoundError("Conversation", conversation_id)
    
    # Get messages
    try:
        msgs = db.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
        return msgs.data or []
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}", exc_info=True)
        return []
