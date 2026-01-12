# FounderGPT Testing Guide

## Pre-Testing Setup (Required)

### 1. Run Database Schema
1. Go to your Supabase Dashboard → SQL Editor
2. Copy and paste the contents of `backend/database/schema.sql`
3. Click "Run" to create all tables and enable pgvector

### 2. Configure Google OAuth
1. In Supabase Dashboard → Authentication → Providers
2. Enable **Google** provider
3. Add your Google OAuth credentials (Client ID & Secret)
4. Ensure redirect URL is set: `https://qqegggjrswgokgnsfjoc.supabase.co/auth/v1/callback`

### 3. Create Storage Bucket
1. In Supabase Dashboard → Storage
2. Click "New bucket"
3. Name: `documents`
4. Make it **public** (or configure RLS policies for authenticated users)

### 4. Verify Environment Variables
Check that `.env` and `frontend/.env.local` have the correct keys (already set).

---

## Testing Flow

### Step 1: Start Servers

**Backend** (already running):
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
npm run dev
```

### Step 2: Test Authentication
1. Open http://localhost:3000
2. Click "Sign in with Google"
3. **Important**: Use an `@silambarasantr.com` email
4. Verify redirect to `/vault` after login

### Step 3: Test Document Upload
1. In Document Vault, click "Upload Document"
2. Upload a PDF file (test with a small PDF, 1-5 pages)
3. Wait for upload to complete
4. Check that document appears in the list
5. **Backend check**: Verify `document_chunks` table has entries in Supabase

### Step 4: Test RAG Chat
1. Navigate to `/chat` (or click "Chat" button)
2. Click "New Chat"
3. Ask a question about your uploaded document
   - Example: "What is this document about?"
   - Example: "Summarize the main points"
4. Verify response includes `[1]`, `[2]` citation badges
5. Click a citation badge → PDF should open in modal
6. Verify it jumps to the correct page

### Step 5: Test Admin Dashboard (if you have admin role)
1. Navigate to `/admin`
2. View stats cards (users, documents, conversations)
3. Try creating a user
4. Try changing a user's role

---

## Expected Behavior

### ✅ Success Indicators
- Login works with `@silambarasantr.com` email
- PDF uploads successfully
- Document appears in vault
- Chat responds with citations
- Citations are clickable
- PDF viewer opens and shows correct page
- Admin dashboard loads (for admin users)

### ❌ Common Issues

**"Access restricted to employee domain only"**
- You're using a non-`@silambarasantr.com` email
- Solution: Use the correct domain

**Upload fails**
- Storage bucket `documents` doesn't exist
- Solution: Create bucket in Supabase Storage

**Chat returns "no documents"**
- Document processing hasn't completed
- Solution: Wait 10-30 seconds after upload, check `document_chunks` table

**Citations don't work**
- Metadata missing in response
- Solution: Check backend logs, verify OpenAI API key is valid

**Admin dashboard shows 403**
- User role is not `admin`
- Solution: Manually update role in Supabase `users` table

---

## Quick Verification Checklist

- [ ] Backend running on :8000
- [ ] Frontend running on :3000
- [ ] Database schema executed
- [ ] Google OAuth configured
- [ ] Storage bucket created
- [ ] Can log in with Google
- [ ] Can upload PDF
- [ ] Can ask questions in chat
- [ ] Citations are clickable
- [ ] PDF viewer works

---

## Next Steps After Testing

If everything works:
1. Deploy frontend to Vercel
2. Deploy backend to your server
3. Update CORS origins in `backend/app/main.py`
4. Set production environment variables

If issues occur:
- Check browser console for errors
- Check backend logs (`uvicorn` output)
- Verify Supabase tables have data
- Test API endpoints directly at http://localhost:8000/api/v1/docs
