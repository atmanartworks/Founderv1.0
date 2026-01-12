from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.db.supabase import get_supabase_client
from app.models.user import User
from typing import Optional

security = HTTPBearer()

async def get_db() -> Client:
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Database connection failed")
    return client

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Client = Depends(get_db)
) -> User:
    token = credentials.credentials
    
    # 1. Verify Token with Supabase Auth
    # Create a client with anon key for auth validation (service role can't validate user tokens)
    try:
        from app.core.config import settings
        from supabase import create_client
        
        # Validate settings
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise HTTPException(
                status_code=500,
                detail="Supabase configuration missing"
            )
        
        # Use anon key for auth validation
        auth_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Validate token
        try:
            # get_user requires a JWT token - if token is invalid, this will fail
            user_response = auth_client.auth.get_user(token)
            auth_user = user_response.user if user_response else None
        except Exception as auth_error:
            # Log the actual error for debugging
            error_str = str(auth_error)
            error_type = type(auth_error).__name__
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Supabase auth error: {error_type}: {error_str}")
            print(f"🔴 Supabase auth error: {error_type}: {error_str}")
            
            # Check if it's an API key issue (the error might be in the response)
            if "Invalid API key" in error_str or "401" in error_str or "invalid" in error_str.lower():
                # This could mean:
                # 1. The anon key in backend .env is wrong
                # 2. The user token is invalid/expired
                # 3. The Supabase project settings changed
                print(f"⚠️  API key validation failed. Debugging info:")
                print(f"   - SUPABASE_URL: {settings.SUPABASE_URL}")
                print(f"   - SUPABASE_KEY (first 30 chars): {settings.SUPABASE_KEY[:30] if settings.SUPABASE_KEY else 'MISSING'}...")
                print(f"   - Token (first 30 chars): {token[:30] if token else 'MISSING'}...")
                print(f"   - Error type: {error_type}")
                print(f"   - Full error: {error_str}")
                
                # More helpful error message
                if "Invalid API key" in error_str:
                    raise HTTPException(
                        status_code=401,
                        detail="Supabase API key is invalid. Please check your SUPABASE_KEY in backend/.env file. It must match the anon key from Supabase dashboard."
                    )
                else:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication failed. Your session may have expired. Please log in again."
                    )
            # For other auth errors, re-raise as 401
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {error_str[:200]}"
            )
        
        if not auth_user:
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication credentials"
            )
        
        # 2. Get user email (no domain restriction for single user)
        user_email = auth_user.email
        if not user_email:
            raise HTTPException(
                status_code=401,
                detail="Email not found in token"
            )

        # 3. Get or create user in public.users table (auto-create for any authenticated user)
        data = db.table("users").select("*").eq("id", auth_user.id).execute()
        
        if not data.data or len(data.data) == 0:
            # Auto-create user profile for first-time login
            print(f"User {user_email} not found in public.users. Auto-creating user profile.")
            user_data = {
                "id": str(auth_user.id),
                "email": user_email,
                "full_name": auth_user.user_metadata.get("full_name") if auth_user.user_metadata else user_email.split("@")[0],
                "role": "user"  # Keep role field for compatibility, but not used for access control
            }
            insert_result = db.table("users").insert(user_data).execute()
            if insert_result.data and len(insert_result.data) > 0:
                return User(**insert_result.data[0])
            else:
                return User(**user_data)
            
        return User(**data.data[0])
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Auth error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )

async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user
