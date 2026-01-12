from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    try:
        if not settings.SUPABASE_URL:
            print("⚠️  Warning: SUPABASE_URL not found.")
            return None
            
        if not settings.SUPABASE_SERVICE_ROLE_KEY:
            print("⚠️  Warning: SUPABASE_SERVICE_ROLE_KEY not found.")
            return None
        
        # Check if service role key is still a placeholder
        if "xxxxxxxx" in settings.SUPABASE_SERVICE_ROLE_KEY or len(settings.SUPABASE_SERVICE_ROLE_KEY) < 100:
            print("⚠️  ERROR: SUPABASE_SERVICE_ROLE_KEY appears to be a placeholder!")
            print("⚠️  Please update SUPABASE_SERVICE_ROLE_KEY in .env with the real service_role key from Supabase Dashboard")
            print("⚠️  Go to: Supabase Dashboard → Project Settings → API → service_role key")
            raise Exception("SUPABASE_SERVICE_ROLE_KEY is not configured. Please set the real service_role key in .env")
            
        # Use SERVICE ROLE KEY to bypass RLS
        client = create_client(
            settings.SUPABASE_URL, 
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        return client
    except Exception as e:
        print(f"❌ Error creating Supabase client: {e}")
        import traceback
        traceback.print_exc()
        return None

# Global client (mostly for admin tasks, or use dependency for per-request)
supabase: Client = get_supabase_client()
