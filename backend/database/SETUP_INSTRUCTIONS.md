# Database Setup Instructions

## Quick Setup (Recommended)

### Option 1: Run All Migrations at Once

1. **Open Supabase SQL Editor**
   - Go to your Supabase project: https://app.supabase.com
   - Navigate to: **SQL Editor** (left sidebar)
   - Click **New Query**

2. **Run Base Schema First**
   - Open `backend/database/schema.sql`
   - Copy the entire contents
   - Paste into SQL Editor
   - Click **Run** (or press Cmd/Ctrl + Enter)

3. **Run All Migrations**
   - Open `backend/database/run_all_migrations.sql`
   - Copy the entire contents
   - Paste into SQL Editor
   - Click **Run**

### Option 2: Run Migrations One by One

If you prefer to run migrations individually:

1. **Base Schema** (Required first)
   ```sql
   -- Run: backend/database/schema.sql
   ```

2. **Migration 1: Document Status**
   ```sql
   -- Run: backend/database/migrations/add_document_status.sql
   ```

3. **Migration 2: Vector Search Function**
   ```sql
   -- Run: backend/database/migrations/add_vector_search_function.sql
   ```

4. **Migration 3: Conversation Logs** ⚠️ **This is what you're missing!**
   ```sql
   -- Run: backend/database/migrations/add_conversation_logs.sql
   ```

5. **Migration 4: Document Versioning**
   ```sql
   -- Run: backend/database/migrations/add_document_versioning.sql
   ```

6. **Migration 5: RLS Policies**
   ```sql
   -- Run: backend/database/migrations/add_comprehensive_rls_policies.sql
   ```

## Verify Setup

After running migrations, verify tables exist:

```sql
-- Check if conversation_logs table exists
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'conversation_logs';

-- Check all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

Expected tables:
- ✅ `users`
- ✅ `folders`
- ✅ `documents`
- ✅ `document_chunks`
- ✅ `conversations`
- ✅ `messages`
- ✅ `conversation_logs` ⚠️ **This is what was missing**
- ✅ `document_versions`
- ✅ `audit_logs`

## Troubleshooting

### Error: "relation does not exist"
- Make sure you ran `schema.sql` first
- Check that migrations ran in order
- Verify you're in the correct database/schema

### Error: "permission denied"
- Make sure you're using the SQL Editor (has proper permissions)
- Check that RLS policies are correctly set up

### Error: "extension vector does not exist"
- Enable the pgvector extension:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

## Quick Fix for Current Error

If you're getting `relation "public.conversation_logs" does not exist`:

**Just run this in Supabase SQL Editor:**

```sql
-- Copy and paste the contents of:
-- backend/database/migrations/add_conversation_logs.sql
```

Or use the quick version:

```sql
CREATE TABLE IF NOT EXISTS public.conversation_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id uuid REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_role app_role NOT NULL,
    organization_id text,
    user_prompt text NOT NULL,
    assistant_response text NOT NULL,
    retrieved_chunks jsonb DEFAULT '[]',
    retrieved_documents jsonb DEFAULT '[]',
    citations jsonb DEFAULT '[]',
    model_name text DEFAULT 'gpt-4',
    temperature float DEFAULT 0.7,
    max_tokens int DEFAULT 2000,
    prompt_tokens int,
    completion_tokens int,
    total_tokens int,
    feedback text,
    feedback_notes text,
    response_quality_score float,
    session_metadata jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_id ON public.conversation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_conversation_id ON public.conversation_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_created_at ON public.conversation_logs(created_at);

ALTER TABLE public.conversation_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own conversation logs" ON public.conversation_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage conversation logs" ON public.conversation_logs
    FOR ALL USING (auth.role() = 'service_role');
```

## Next Steps

After running migrations:
1. ✅ Restart your backend server
2. ✅ Test the application
3. ✅ Verify no more "relation does not exist" errors

---

**Need Help?** Check the migration files in `backend/database/migrations/` for detailed SQL.

