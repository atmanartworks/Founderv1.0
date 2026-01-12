from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "FounderGPT API"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENV: str = "development"
    PORT: int = 8000
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"  # Updated to gpt-4o
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    STORAGE_BUCKET_NAME: str = "GPTv1"
    
    # LlamaCloud (Optional - for advanced document parsing)
    # Set to None or empty to disable Llama Parse (will use basic readers)
    LLAMA_CLOUD_API_KEY: Optional[str] = None
    ENABLE_LLAMA_PARSE: bool = False  # Set to False if not using Llama Parse
    
    # RAG Configuration
    RAG_CHUNK_LIMIT: int = 10  # Increased for large documents
    CHUNK_SIZE: int = 2048  # Increased for better context (was 1024)
    CHUNK_OVERLAP: int = 200  # Increased overlap for better continuity (was 20)
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Feature Flags
    ENABLE_STREAMING: bool = True
    ENABLE_CITATION_HIGHLIGHTING: bool = True
    ENABLE_CONVERSATION_LOGGING: bool = True

    class Config:
        env_file = "../.env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env

settings = Settings()
