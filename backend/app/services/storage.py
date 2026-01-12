from supabase import Client
from fastapi import UploadFile
from app.core.config import settings
from app.db.supabase import get_supabase_client
import uuid
from datetime import datetime
from io import BytesIO

class StorageService:
    def __init__(self):
        self.bucket_name = "GPTv1"
        self.client = get_supabase_client()

    async def upload_file(self, file: UploadFile, owner_id: str) -> str:
        """
        Uploads a file to Supabase Storage and returns the path.
        """
        # Create unique path: {owner_id}/{uuid}/{filename}
        file_ext = file.filename.split(".")[-1]
        file_path = f"{owner_id}/{uuid.uuid4()}/{file.filename}"
        
        file_content = await file.read()
        
        # Upload
        # Note: If bucket doesn't exist, this might fail unless we ensure it exists.
        # Supabase-py storage client usage:
        res = self.client.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        return file_path
    
    async def upload_file_from_buffer(
        self, 
        buffer: BytesIO, 
        filename: str, 
        content_type: str,
        owner_id: str,
        folder_prefix: str = ""
    ) -> str:
        """
        Upload a file from a BytesIO buffer to Supabase Storage.
        """
        try:
            # Generate unique path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = filename.replace(" ", "_")
            storage_path = f"{folder_prefix}/{owner_id}/{timestamp}_{safe_filename}" if folder_prefix else f"{owner_id}/{timestamp}_{safe_filename}"
            
            # Upload to Supabase Storage
            buffer.seek(0)
            self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=buffer.read(),
                file_options={"content-type": content_type}
            )
            
            return storage_path
        except Exception as e:
            print(f"Buffer upload error: {e}")
            raise Exception(f"Failed to upload buffer: {str(e)}")

storage_service = StorageService()
