from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Literal, Optional
from uuid import UUID
from openai import OpenAI
from app.api import deps
from app.models.user import User
from app.core.config import settings
from app.db.supabase import get_supabase_client
from app.services.document_generator import document_generator
from app.services.storage import StorageService
from fastapi.responses import StreamingResponse
import io

router = APIRouter()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class GenerateDocumentRequest(BaseModel):
    document_type: Literal["report", "summary", "proposal", "analysis"]
    topic: str
    instructions: Optional[str] = None
    format: Literal["pdf", "docx", "both"] = "pdf"

@router.post("/generate")
async def generate_document(
    request: GenerateDocumentRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Generate a document using GPT-4 based on user input.
    """
    try:
        # Build prompt based on document type
        system_prompt = f"""You are a professional document writer. Generate a well-structured {request.document_type} 
about the given topic. Use clear headings, bullet points where appropriate, and maintain a professional tone.
Format the output in plain text with clear section breaks using double newlines."""

        user_prompt = f"""Topic: {request.topic}

{f'Additional Instructions: {request.instructions}' if request.instructions else ''}

Please generate a comprehensive {request.document_type}."""

        # Generate content with GPT-4
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        title = f"{request.document_type.title()}: {request.topic[:50]}"

        # Generate documents
        storage_service = StorageService()
        db = get_supabase_client()
        generated_files = []

        if request.format in ["pdf", "both"]:
            pdf_buffer = document_generator.generate_pdf(
                content, 
                title,
                author=current_user.full_name or current_user.email,
                metadata={
                    "document_type": request.document_type,
                    "topic": request.topic,
                    "generated_by": str(current_user.id)
                }
            )
            pdf_filename = f"{request.document_type}_{request.topic[:30].replace(' ', '_')}.pdf"
            
            # Upload to storage in 'generated' folder
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
                    "document_type": request.document_type,
                    "topic": request.topic
                }
            }
            pdf_doc = db.table("documents").insert(doc_data).execute()
            generated_files.append({
                "id": pdf_doc.data[0]["id"] if pdf_doc.data else None,
                "format": "pdf",
                "filename": pdf_filename,
                "storage_path": pdf_path
            })

        if request.format in ["docx", "both"]:
            docx_buffer = document_generator.generate_docx(
                content, 
                title,
                author=current_user.full_name or current_user.email,
                metadata={
                    "document_type": request.document_type,
                    "topic": request.topic,
                    "generated_by": str(current_user.id)
                }
            )
            docx_filename = f"{request.document_type}_{request.topic[:30].replace(' ', '_')}.docx"
            
            # Upload to storage
            docx_path = await storage_service.upload_file_from_buffer(
                docx_buffer,
                docx_filename,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                str(current_user.id),
                folder_prefix="generated"
            )
            
            # Save to documents table
            doc_data = {
                "owner_id": str(current_user.id),
                "title": f"{title} (DOCX)",
                "storage_path": docx_path,
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "metadata": {
                    "generated": True,
                    "document_type": request.document_type,
                    "topic": request.topic
                }
            }
            docx_doc = db.table("documents").insert(doc_data).execute()
            generated_files.append({
                "id": docx_doc.data[0]["id"] if docx_doc.data else None,
                "format": "docx",
                "filename": docx_filename,
                "storage_path": docx_path
            })

        return {
            "message": "Document(s) generated successfully",
            "files": generated_files,
            "content_preview": content[:200] + "..."
        }

    except Exception as e:
        print(f"Document generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")
