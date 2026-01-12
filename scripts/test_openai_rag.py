
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

# Load .env from current directory
load_dotenv()

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from app.services.ingestion import ingestion_service
from app.services.chat import chat_service
from app.db.supabase import get_supabase_client
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure API keys are present
if not settings.OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY module not found even after loading .env")
    # Try setting manually if environment variable is present but not picked up by pydantic
    if os.getenv("OPENAI_API_KEY"):
        settings.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    else:
        logger.error("OPENAI_API_KEY not set in environment")

if not settings.SUPABASE_URL:
    if os.getenv("SUPABASE_URL"):
        settings.SUPABASE_URL = os.getenv("SUPABASE_URL")
    if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        settings.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

@dataclass
class MockUser:
    id: uuid.UUID

async def run_test():
    logger.info("Starting OpenAI RAG Verification Test")
    
    # 1. Setup User and Client
    client = get_supabase_client()
    
    # Create a fresh test user
    try:
        test_email = f"test_{uuid.uuid4()}@example.com"
        logger.info(f"Creating new test user: {test_email}")
        user_response = client.auth.admin.create_user({
            "email": test_email,
            "password": "password123",
            "email_confirm": True
        })
        # Check structure of response
        if hasattr(user_response, 'user'):
            user_id = uuid.UUID(user_response.user.id)
        else:
            # Fallback for different library versions
            user_id = uuid.UUID(user_response.id)
            
        logger.info(f"Created test user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        # Try listing again as fallback
        try:
             admin_users = client.auth.admin.list_users()
             if admin_users and len(admin_users) > 0:
                 user_id = uuid.UUID(admin_users[0].id)
             else:
                 raise Exception("No users available")
        except:
             raise Exception("Failed to setup user")

    user = MockUser(id=user_id)

    # Check if we need to insert into public.users
    try:
        # Try to insert into public.users (triggers might have done it, so we upsert or ignore conflict)
        client.table("users").upsert({
            "id": str(user_id), 
            "email": test_email, 
            "full_name": "Test User",
            # Add any other required fields for your schema
        }).execute()
        logger.info("Inserted/Updated public.users")
    except Exception as e:
        logger.info(f"Skipping public.users insert: {e}")


    # 2. Create Test Document
    doc_id = uuid.uuid4()
    filename = "test_openai_rag.txt"
    content = "The secret code for the OpenAI migration is: BLUE-MIGRATION-SUCCESS-2024."
    file_path = f"{user_id}/{filename}"
    
    logger.info(f"Uploading test file to Supabase Storage: {file_path}")
    
    try:
        # Create temp file
        with open("temp_test_doc.txt", "w") as f:
            f.write(content)
            
        # Upload to Storage
        with open("temp_test_doc.txt", "rb") as f:
            client.storage.from_("GPTv1").upload(
                file_path,
                f,
                {"content-type": "text/plain"}
            )
            
        # Register in DB
        logger.info("Registering document in DB")
        client.table("documents").insert({
            "id": str(doc_id),
            "owner_id": str(user_id),
            "title": filename,
            "storage_path": file_path,
            "mime_type": "text/plain",
            "status": "processing"
        }).execute()
        
        # 3. Trigger Ingestion
        logger.info("Triggering Ingestion Service")
        await ingestion_service.process_document(
            file_path=file_path,
            document_id=doc_id,
            mime_type="text/plain"
        )
        logger.info("Ingestion completed")
        
        # 4. Test Chat
        query = "What is the secret code for the migration?"
        logger.info(f"Testing Chat with query: {query}")
        
        response = await chat_service.generate_response(
            query=query,
            user=user
        )
        
        print("\n" + "="*50)
        print(f"RESPONSE:\n{response['answer']}")
        print("="*50 + "\n")
        
        # 5. Verify
        assert "BLUE-MIGRATION-SUCCESS-2024" in response['answer'], "Answer should contain the secret code"
        assert len(response['citations']) > 0, "Citations should not be empty"
        assert response['citations'][0]['document_title'] == filename, "Citation should list the filename"
        
        logger.info("✅ Verification SUCCESS!")
        
    except Exception as e:
        logger.error(f"❌ Verification FAILED: {e}", exc_info=True)
        raise
    finally:
        # 6. Cleanup
        logger.info("Cleaning up...")
        try:
            # Delete from DB (document)
            # Fetch metadata to delete from OpenAI first?
            # Ingestion service creates OpenAI file and vector store file.
            # We implemented delete_document endpoint logic but here we are manual.
            
            # Retrieve OpenAI file ID
            doc = client.table("documents").select("metadata").eq("id", str(doc_id)).single().execute()
            if doc.data:
                meta = doc.data.get("metadata", {})
                openai_file_id = meta.get("openai_file_id")
                vector_store_id = meta.get("vector_store_id")
                
                if openai_file_id:
                    logger.info(f"Deleting OpenAI file: {openai_file_id}")
                    try:
                        ingestion_service.client.files.delete(openai_file_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete OpenAI file: {e}")
            
            client.table("documents").delete().eq("id", str(doc_id)).execute()
            client.storage.from_("GPTv1").remove([file_path])
            logger.info("Cleanup completed")
            
            if os.path.exists("temp_test_doc.txt"):
                os.remove("temp_test_doc.txt")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
