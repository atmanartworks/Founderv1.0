# Service Role Key Setup - CRITICAL!

## The Problem

You're getting "Streaming request failed" errors because the **Service Role Key** is still a placeholder in your `.env` file.

## Why This Matters

The backend uses the **Service Role Key** to:
- Query the database (users, documents, conversations)
- Bypass Row-Level Security (RLS) for backend operations
- Access all data regardless of user permissions

**Without a valid service role key, the backend cannot access the database!**

## How to Fix

### Step 1: Get Your Service Role Key

1. Go to **Supabase Dashboard**: https://app.supabase.com
2. Select your project
3. Go to **Project Settings** (gear icon) → **API**
4. Find the **service_role** key (NOT the anon key)
5. **Copy the entire key** (it's long, starts with `eyJhbGci...`)

⚠️ **IMPORTANT**: This is the **service_role** key, NOT the anon key!

### Step 2: Update Backend `.env`

Open `backend/.env` (or root `.env` if that's where your config is) and update:

```env
# Supabase Service Role Key (SECRET - backend only, never expose to client)
# Get this from: Supabase Dashboard → Project Settings → API → service_role key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFxZWdnZ2pyc3dnb2tnbnNmam9jIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzgyNDQ5NCwiZXhwIjoyMDgzNDAwNDk0fQ.YOUR_ACTUAL_SERVICE_ROLE_KEY_HERE
```

**Replace the placeholder** (`xxxxxxxx...`) with your actual service_role key.

### Step 3: Restart Backend

After updating `.env`:

```bash
cd backend
source venv/bin/activate
# Kill existing process
pkill -f "uvicorn app.main:app"
# Restart
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Verify

Check backend logs for errors:
```bash
tail -f /tmp/backend.log
```

You should NOT see:
- "SUPABASE_SERVICE_ROLE_KEY is not configured"
- "Invalid API key" errors from database queries

## Key Differences

| Key Type | Where Used | Purpose |
|----------|-----------|---------|
| **anon key** | Frontend + Backend auth | Validates user JWT tokens |
| **service_role key** | Backend only | Database queries, bypasses RLS |

## Security Warning

🔒 **NEVER expose the service_role key to the frontend!**

- ✅ Use in backend `.env` only
- ✅ Never commit to git
- ✅ Never send to client
- ✅ Keep it secret!

The service_role key bypasses all security - it has full access to your database!

## Current Status

Your `.env` currently has:
```env
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...xxxxxxxx...  # ❌ PLACEHOLDER
```

You need to replace it with the real key from Supabase Dashboard.

## After Fixing

Once you update the service_role key and restart the backend:
1. ✅ Database queries will work
2. ✅ Streaming requests will succeed
3. ✅ Chat will function properly
4. ✅ Document uploads will work

## Quick Checklist

- [ ] Get service_role key from Supabase Dashboard
- [ ] Update `SUPABASE_SERVICE_ROLE_KEY` in `.env`
- [ ] Restart backend
- [ ] Test chat - should work now!

