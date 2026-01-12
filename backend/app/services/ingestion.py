import os
import logging
import asyncio
from uuid import UUID
from typing import Optional
import tempfile

from openai import OpenAI
from app.core.config import settings
from app.db.supabase import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.supabase = get_supabase_client()

    def _get_user_vector_store_id(self, user_id: str) -> Optional[str]:
        """
        Finds the user's vector store using the naming convention.
        """
        store_name = f"User_{user_id}_Store"
        try:
            # We list generic vector stores. In a real prod env, we'd store this ID in the user profile.
            vector_stores = self.client.vector_stores.list(limit=100)
            for store in vector_stores.data:
                if store.name == store_name:
                    return store.id
            return None
        except Exception as e:
            logger.error(f"Error finding vector store: {e}")
            return None

    def _create_user_vector_store(self, user_id: str) -> str:
        """
        Creates a new vector store for the user.
        """
        store_name = f"User_{user_id}_Store"
        try:
            logger.info(f"Creating new Vector Store: {store_name}")
            vector_store = self.client.vector_stores.create(
                name=store_name
            )
            return vector_store.id
        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            raise

    async def process_document(self, file_path: str, document_id: UUID, mime_type: str):
        """
        Pure OpenAI Pipeline:
        1. Download file from Supabase Storage
        2. Upload to OpenAI Files
        3. Attach to User's Vector Store
        4. Wait for processing
        5. Update Document metadata (openai_file_id)
        """
        temp_file_path = None
        try:
            logger.info(f"Starting generic ingestion for doc: {document_id}")
            
            # 1. Download from Supabase
            bucket = "GPTv1"
            storage_bucket = self.supabase.storage.from_(bucket)
            
            logger.info(f"Downloading {file_path} from bucket {bucket}")
            try:
                res = storage_bucket.download(file_path)
            except Exception as e:
                logger.warning(f"Direct download failed: {e}. Trying URL encoded path.")
                import urllib.parse
                encoded_path = urllib.parse.quote(file_path, safe='/')
                res = storage_bucket.download(encoded_path)
            
            if not res:
                raise Exception(f"Failed to download file: {file_path} - Empty response")
            
            # Create temp file safely
            # We preserve extension for OpenAI to detect file type
            ext = os.path.splitext(file_path)[1]
            if not ext:
                 ext = ".txt" # Default fallback
                 
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                temp_file_path = tmp.name
                tmp.write(res)
                
            logger.info(f"File saved locally to {temp_file_path} ({len(res)} bytes)")
                
            # 2. Upload to OpenAI
            logger.info("Uploading file to OpenAI...")
            with open(temp_file_path, "rb") as f:
                openai_file = self.client.files.create(
                    file=f,
                    purpose="assistants"
                )
            logger.info(f"OpenAI File ID: {openai_file.id}")

            # 3. Get document owner to find correct Vector Store
            doc_info = self.supabase.table("documents").select("owner_id").eq("id", str(document_id)).single().execute()
            if not doc_info.data:
                raise Exception(f"Document {document_id} not found in DB")
            
            user_id = doc_info.data["owner_id"]
            
            # 4. Add to Vector Store
            vs_id = self._get_user_vector_store_id(user_id)
            if not vs_id:
                vs_id = self._create_user_vector_store(user_id)
            
            logger.info(f"Attaching file {openai_file.id} to Vector Store {vs_id}")
            self.client.vector_stores.files.create_and_poll(
                vector_store_id=vs_id,
                file_id=openai_file.id
            )
            
            # 5. Update DB with OpenAI File ID
            self.supabase.table("documents").update({
                "metadata": {"openai_file_id": openai_file.id},
                "status": "completed", 
                "chunk_count": 1 
            }).eq("id", str(document_id)).execute()
            
            logger.info(f"Document {document_id} successfully registered with OpenAI")
            return 1 

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")

ingestion_service = IngestionService()
