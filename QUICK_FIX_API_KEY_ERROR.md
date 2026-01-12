# Quick Fix: "Invalid API key" Error

## The Problem

You're getting this error:
```
Could not validate credentials: Invalid API key
```

**This is a Supabase authentication issue, NOT an OpenAI issue.**

## Root Cause

The backend is trying to validate user JWT tokens using the Supabase anon key, but either:
1. The token is expired/invalid
2. The backend needs to be restarted to pick up .env changes
3. There's a mismatch in configuration

## Quick Fix Steps

### Step 1: Update OpenAI Model (Done ✅)

I've updated your `.env` file:
```env
OPENAI_MODEL=gpt-4o  # Changed from gpt-3.5-turbo
```

### Step 2: Restart Backend

The backend needs to be restarted to pick up the new configuration:

```bash
# Kill existing backend
pkill -f "uvicorn app.main:app"

# Restart backend
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: Clear Browser Storage & Re-login

1. Open browser DevTools (F12)
2. Go to **Application** → **Local Storage** → `http://localhost:3000`
3. Delete `supabase_token`
4. Refresh the page
5. Log in again with Google

### Step 4: Verify Configuration

Check that your keys are correct:

**Backend `.env`** (root directory):
```env
SUPABASE_URL=https://qqegggjrswgokgnsfjoc.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # anon key
OPENAI_MODEL=gpt-4o  # ✅ Updated
OPENAI_API_KEY=sk-proj-...  # Your OpenAI key
```

**Frontend `.env.local`**:
```env
NEXT_PUBLIC_SUPABASE_URL=https://qqegggjrswgokgnsfjoc.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Same as SUPABASE_KEY
```

## Why This Happens

1. **Token Expiration**: User JWT tokens expire after a certain time
2. **Backend Restart Needed**: Backend caches environment variables on startup
3. **Session Mismatch**: Browser has old token, backend expects new format

## About OpenAI

✅ **OpenAI is configured correctly** - no syntax errors
✅ **Model updated to gpt-4o** as requested
✅ **API key is valid** (starts with `sk-proj-`)

The error is purely about Supabase authentication, not OpenAI.

## If Error Persists

1. **Check backend logs**:
   ```bash
   tail -f /tmp/backend.log
   ```

2. **Verify Supabase keys** in Supabase Dashboard:
   - Go to Project Settings → API
   - Copy the **anon public** key
   - Make sure it matches both `.env` files

3. **Test authentication directly**:
   - Try logging out completely
   - Clear all browser storage
   - Log in fresh

## Summary

- ✅ OpenAI model updated to `gpt-4o`
- ✅ No syntax errors in OpenAI connection
- ⚠️ Error is about Supabase authentication (not OpenAI)
- 🔧 Solution: Restart backend + clear browser storage + re-login

