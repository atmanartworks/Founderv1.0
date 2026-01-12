from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

# CORS - Configure for development and production
# Get frontend URL from environment or default
import os
frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL") or os.getenv("VERCEL_URL", "")

# In development, allow localhost and network IPs
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Add production frontend URL if available
if frontend_url:
    if not frontend_url.startswith("http"):
        frontend_url = f"https://{frontend_url}"
    origins.append(frontend_url)

# In development, be more permissive
if settings.ENV == "development" or os.getenv("VERCEL") is None:
    # Ensure all common localhost variants are included
    origins = list(set(origins))  # Remove duplicates
else:
    # Production: use environment-based origins
    origins = [origin for origin in origins if origin]  # Filter empty strings

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=3600,
)

@app.get("/")
async def root():
    return {"message": "Welcome to FounderGPT API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

app.include_router(api_router, prefix=settings.API_V1_STR)
