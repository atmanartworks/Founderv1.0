-- ============================================================================
-- COMPLETE DATABASE RESET AND RECREATION
-- ============================================================================
-- This script drops ALL tables, policies, functions, and types
-- Then recreates a simplified schema for single-user system (no RBAC)
-- ============================================================================
-- WARNING: This will DELETE ALL DATA!
-- Run this in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: Drop all policies
-- ============================================================================

-- Drop all policies on all tables
DO $$ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT schemaname, tablename, policyname 
              FROM pg_policies 
              WHERE schemaname = 'public') 
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', 
                       r.policyname, r.schemaname, r.tablename);
    END LOOP;
END $$;

-- ============================================================================
-- STEP 2: Drop all functions
-- ============================================================================

DROP FUNCTION IF EXISTS public.search_document_chunks(vector, uuid, float, int) CASCADE;
DROP FUNCTION IF EXISTS public.get_user_role(uuid) CASCADE;
DROP FUNCTION IF EXISTS public.is_admin(uuid) CASCADE;
DROP FUNCTION IF EXISTS public.has_folder_access(uuid, uuid) CASCADE;
DROP FUNCTION IF EXISTS public.has_document_access(uuid, uuid) CASCADE;
DROP FUNCTION IF EXISTS public.create_document_version(uuid, text, jsonb, uuid) CASCADE;
DROP FUNCTION IF EXISTS public.get_document_version_history(uuid) CASCADE;
DROP FUNCTION IF EXISTS public.rollback_document_version(uuid, int) CASCADE;

-- ============================================================================
-- STEP 3: Drop all tables (in correct order due to foreign keys)
-- ============================================================================

DROP TABLE IF EXISTS public.conversation_logs CASCADE;
DROP TABLE IF EXISTS public.messages CASCADE;
DROP TABLE IF EXISTS public.conversations CASCADE;
DROP TABLE IF EXISTS public.document_versions CASCADE;
DROP TABLE IF EXISTS public.document_chunks CASCADE;
DROP TABLE IF EXISTS public.documents CASCADE;
DROP TABLE IF EXISTS public.folders CASCADE;
DROP TABLE IF EXISTS public.audit_logs CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

-- ============================================================================
-- STEP 4: Drop types
-- ============================================================================

DROP TYPE IF EXISTS public.app_role CASCADE;

-- ============================================================================
-- STEP 5: Enable extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- STEP 6: Create simplified schema (single user, no RBAC)
-- ============================================================================

-- Users Table (simplified - no roles needed, but keep for compatibility)
CREATE TABLE public.users (
    id uuid REFERENCES auth.users ON DELETE CASCADE NOT NULL PRIMARY KEY,
    email text NOT NULL,
    full_name text,
    role text DEFAULT 'user', -- Keep for compatibility, not used for access control
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Documents (simplified - no folders, no permissions)
CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    owner_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
    
    title text NOT NULL,
    storage_path text NOT NULL, -- Path in Supabase Storage
    mime_type text,
    metadata jsonb DEFAULT '{}',
    
    -- Document processing status
    status text DEFAULT 'processing' NOT NULL, -- 'processing', 'completed', 'failed'
    chunk_count int DEFAULT 0,
    error_message text,
    
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Document Chunks (for RAG)
CREATE TABLE public.document_chunks (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id uuid REFERENCES public.documents(id) ON DELETE CASCADE,
    
    content text NOT NULL,
    page_number int,
    chunk_index int,
    
    -- Metadata for citations (simplified - no highlighting)
    start_char_idx int,
    end_char_idx int,
    
    -- Vector Embedding (OpenAI text-embedding-3-large = 3072, but we'll use 1536 for compatibility)
    embedding vector(1536),
    
    metadata jsonb DEFAULT '{}'
);

-- Index for vector search
CREATE INDEX ON public.document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON public.document_chunks (document_id);
CREATE INDEX ON public.documents (status);
CREATE INDEX ON public.documents (owner_id);

-- Chat System
CREATE TABLE public.conversations (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
    title text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE public.messages (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id uuid REFERENCES public.conversations(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content text NOT NULL,
    
    -- Citations: Array of objects { label, document_name, page_number, document_id }
    citations jsonb DEFAULT '[]',
    
    created_at timestamptz DEFAULT now()
);

-- Conversation Logs (for developer analytics)
CREATE TABLE public.conversation_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- User and conversation info
    user_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id uuid REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_role text NOT NULL,
    
    -- Conversation data
    user_prompt text NOT NULL,
    assistant_response text NOT NULL,
    
    -- RAG context
    retrieved_chunks jsonb DEFAULT '[]', -- Array of chunk IDs and content used
    retrieved_documents jsonb DEFAULT '[]', -- Array of document IDs referenced
    citations jsonb DEFAULT '[]', -- Citation objects from response
    
    -- Model and generation info
    model_name text DEFAULT 'gpt-4o',
    temperature float DEFAULT 0.7,
    max_tokens int DEFAULT 2000,
    tokens_used int, -- Total tokens consumed
    
    -- Feedback and quality signals
    feedback text, -- 'positive', 'negative', 'neutral', or null
    feedback_notes text,
    response_quality_score float,
    
    -- Metadata
    session_metadata jsonb DEFAULT '{}', -- Additional session context (mode, etc.)
    created_at timestamptz DEFAULT now()
);

-- Indexes for conversation_logs
CREATE INDEX idx_conversation_logs_user_id ON public.conversation_logs(user_id);
CREATE INDEX idx_conversation_logs_conversation_id ON public.conversation_logs(conversation_id);
CREATE INDEX idx_conversation_logs_created_at ON public.conversation_logs(created_at);
CREATE INDEX idx_conversation_logs_user_role ON public.conversation_logs(user_role);

-- ============================================================================
-- STEP 7: Create simplified vector search function (no RBAC)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.search_document_chunks(
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    page_number int,
    chunk_index int,
    start_char_idx int,
    end_char_idx int,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.content,
        dc.page_number,
        dc.chunk_index,
        dc.start_char_idx,
        dc.end_char_idx,
        dc.metadata,
        (dc.embedding <#> query_embedding) * -1 AS similarity
    FROM
        public.document_chunks dc
    WHERE
        dc.embedding IS NOT NULL
        AND (dc.embedding <#> query_embedding) * -1 > similarity_threshold
    ORDER BY
        dc.embedding <#> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- STEP 8: Simplified RLS (single user - minimal policies)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_logs ENABLE ROW LEVEL SECURITY;

-- Users: Can read their own profile
CREATE POLICY "Users can read own profile" ON public.users
    FOR SELECT
    USING (auth.uid() = id);

-- Documents: All authenticated users can access all documents (single user system)
CREATE POLICY "Authenticated users can access all documents" ON public.documents
    FOR ALL
    USING (auth.role() = 'authenticated');

-- Document chunks: All authenticated users can access all chunks
CREATE POLICY "Authenticated users can access all chunks" ON public.document_chunks
    FOR ALL
    USING (auth.role() = 'authenticated');

-- Conversations: Users can access their own conversations
CREATE POLICY "Users can access own conversations" ON public.conversations
    FOR ALL
    USING (auth.uid() = user_id);

-- Messages: Users can access messages in their conversations
CREATE POLICY "Users can access own messages" ON public.messages
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = messages.conversation_id
            AND c.user_id = auth.uid()
        )
    );

-- Conversation logs: Users can read their own logs
CREATE POLICY "Users can read own conversation logs" ON public.conversation_logs
    FOR SELECT
    USING (auth.uid() = user_id);

-- Service role: Full access for backend operations
CREATE POLICY "Service role full access users" ON public.users
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access documents" ON public.documents
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access chunks" ON public.document_chunks
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access conversations" ON public.conversations
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access messages" ON public.messages
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access conversation logs" ON public.conversation_logs
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- STEP 9: Grant permissions
-- ============================================================================

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_role;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Database reset and recreation complete!';
    RAISE NOTICE '✅ All tables, policies, and functions have been recreated for single-user system';
    RAISE NOTICE '✅ RLS policies are simplified (no RBAC)';
    RAISE NOTICE '✅ Vector search function created (no user filtering)';
END $$;

