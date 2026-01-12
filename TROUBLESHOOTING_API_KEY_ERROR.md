# Troubleshooting: "Invalid API key" Error

## Error Message

```
Could not validate credentials: {'message': 'JSON could not be generated', 'code': 401, 
'hint': 'Refer to full message for details', 
'details': 'b\'{"message":"Invalid API key","hint":"Double check your Supabase `anon` or `service_role` API key."}\''}
```

## Root Cause

This is a **Supabase API key issue**, NOT an OpenAI issue. The backend is trying to validate user JWT tokens using the Supabase anon key, but something is wrong.

## Why This Happens

1. **Backend uses anon key to validate user tokens** (line 36 in `deps.py`)
2. **The anon key in backend `.env` must match the frontend `.env.local`**
3. **If keys don't match, token validation fails**

## Solution Steps

### Step 1: Verify Supabase Keys Match

**Frontend** (`frontend/.env.local`):
```env
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Backend** (`backend/.env` or root `.env`):
```env
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**These must be EXACTLY the same!**

### Step 2: Get Correct Keys from Supabase

1. Go to **Supabase Dashboard** → **Project Settings** → **API**
2. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY` (backend) and `NEXT_PUBLIC_SUPABASE_ANON_KEY` (frontend)
   - **service_role** key → `SUPABASE_SERVICE_ROLE_KEY` (backend only, secret!)

### Step 3: Update Configuration Files

**Backend `.env` (root directory)**:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # anon key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # service_role key
```

**Frontend `.env.local`**:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # same as SUPABASE_KEY above
```

### Step 4: Restart Backend

After updating `.env`:
```bash
cd backend
source venv/bin/activate
# Kill existing process
pkill -f "uvicorn app.main:app"
# Restart
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Clear Browser Storage

1. Open browser DevTools (F12)
2. Go to **Application** → **Local Storage**
3. Delete `supabase_token`
4. Refresh page and login again

## Common Issues

### Issue 1: Keys Don't Match

**Symptom**: Error persists after updating keys

**Solution**: 
- Double-check that `SUPABASE_KEY` in backend `.env` is EXACTLY the same as `NEXT_PUBLIC_SUPABASE_ANON_KEY` in frontend `.env.local`
- Make sure there are no extra spaces or quotes

### Issue 2: Wrong Key Type

**Symptom**: "Invalid API key" error

**Solution**:
- Backend `SUPABASE_KEY` must be the **anon/public** key (NOT service_role)
- Service role key is only for `SUPABASE_SERVICE_ROLE_KEY`

### Issue 3: Token Expired

**Symptom**: Works sometimes, fails other times

**Solution**:
- Clear browser localStorage
- Log out and log back in
- Check if token refresh is working

### Issue 4: Environment File Not Loaded

**Symptom**: Backend still using old keys

**Solution**:
- Make sure `.env` file is in the correct location (root directory or `backend/` directory)
- Check `backend/app/core/config.py` - it looks for `env_file = "../.env"` (one level up from backend/)
- Restart backend after changing `.env`

## Verification

### Check Backend Configuration

```bash
cd backend
source venv/bin/activate
python -c "from app.core.config import settings; print(f'SUPABASE_URL: {settings.SUPABASE_URL}'); print(f'SUPABASE_KEY: {settings.SUPABASE_KEY[:30]}...')"
```

### Check Frontend Configuration

In browser console:
```javascript
console.log('SUPABASE_URL:', process.env.NEXT_PUBLIC_SUPABASE_URL);
console.log('SUPABASE_KEY:', process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.substring(0, 30));
```

## About OpenAI (Not the Issue Here)

The error is **NOT about OpenAI**. However, I noticed your `.env` has:
```
OPENAI_MODEL=gpt-3.5-turbo
```

But you want `gpt-4o`. I've updated this in the `.env` file.

**OpenAI Configuration**:
- `OPENAI_API_KEY` - Your OpenAI API key (starts with `sk-`)
- `OPENAI_MODEL` - Model name (now set to `gpt-4o`)

No syntax errors in OpenAI connection - the issue is purely Supabase authentication.

## Quick Fix Checklist

- [ ] Verify `SUPABASE_KEY` in backend `.env` matches `NEXT_PUBLIC_SUPABASE_ANON_KEY` in frontend `.env.local`
- [ ] Both keys are the **anon/public** key (not service_role)
- [ ] Restart backend after updating `.env`
- [ ] Clear browser localStorage and login again
- [ ] Check backend logs for detailed error messages

