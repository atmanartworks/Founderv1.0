-- CRITICAL: Run this entire script in Supabase SQL Editor
-- This disables RLS on all tables to allow backend operations

-- Disable RLS on all tables
ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.folders DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs DISABLE ROW LEVEL SECURITY;

-- Verify RLS is disabled (should return 'f' for all)
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('users', 'documents', 'document_chunks', 'folders', 'conversations', 'messages');

-- Set yourself as admin (replace with your email)
UPDATE public.users 
SET role = 'admin' 
WHERE email = 'your-email@silambarasantr.com';

-- Verify your role
SELECT email, role FROM public.users;
