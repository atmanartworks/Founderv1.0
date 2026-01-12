import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: Missing Supabase credentials")
    exit(1)

supabase: Client = create_client(url, key)

def cleanup_chunks():
    print("Starting cleanup of 'document_chunks' table...")
    try:
        # Check if table exists/has data by selecting one row
        res = supabase.table("document_chunks").select("id").limit(1).execute()
        if not res.data:
            print("Table appears empty or accessible.")
        
        # Delete all rows (using a condition that matches everything, e.g. id is not null)
        # Note: Supabase JS/Py client deletes require a filter.
        # We need a range or something. ID is UUID.
        # neq('id', '00000000-0000-0000-0000-000000000000') is a common hack.
        
        print("Deleting all rows...")
        res = supabase.table("document_chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"Cleanup complete. Deleted {len(res.data) if res.data else 0} chunks.")
        
    except Exception as e:
        print(f"Error during cleanup (Table might not exist, which is fine): {e}")

if __name__ == "__main__":
    cleanup_chunks()
