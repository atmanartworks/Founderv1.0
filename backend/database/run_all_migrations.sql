-- ============================================
-- FounderGPT Database Setup - Run All Migrations
-- ============================================
-- Run this script in your Supabase SQL Editor
-- Order: schema.sql first, then migrations in order
-- ============================================

-- Step 1: Run the base schema (if not already run)
-- Copy and paste the contents of schema.sql first, then run these migrations

-- ============================================
-- Migration 1: Add document status tracking
-- ============================================
-- Add status column to documents table
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'processing' NOT NULL;

-- Add chunk_count column to documents table
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS chunk_count INT DEFAULT 0;

-- Add error_message column to documents table
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Create index on status for faster querying
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents (status);

-- ============================================
-- Migration 2: Add vector search function
-- ============================================
CREATE OR REPLACE FUNCTION public.search_document_chunks(
    query_embedding vector(1536),
    user_id_param uuid,
    similarity_threshold float,
    match_count int
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
    JOIN
        public.documents d ON dc.document_id = d.id
    WHERE
        -- Permission check: user owns the document OR document allows user's role OR document allows specific user
        (
            d.owner_id = user_id_param
            OR user_id_param = ANY(d.allowed_users)
            OR EXISTS (
                SELECT 1 FROM public.users u
                WHERE u.id = user_id_param
                AND u.role = ANY(d.allowed_roles)
            )
        )
        AND (dc.embedding <#> query_embedding) * -1 > similarity_threshold
    ORDER BY
        dc.embedding <#> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- Migration 3: Add conversation logs table
-- ============================================
CREATE TABLE IF NOT EXISTS public.conversation_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- User and conversation info
    user_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id uuid REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_role app_role NOT NULL,
    
    -- Anonymized identifiers (for multi-tenant support)
    organization_id text, -- Optional: for multi-tenant segmentation
    
    -- Conversation data
    user_prompt text NOT NULL,
    assistant_response text NOT NULL,
    
    -- RAG context
    retrieved_chunks jsonb DEFAULT '[]', -- Array of chunk IDs and content used
    retrieved_documents jsonb DEFAULT '[]', -- Array of document IDs referenced
    citations jsonb DEFAULT '[]', -- Citation objects from response
    
    -- Model and generation info
    model_name text DEFAULT 'gpt-4',
    temperature float DEFAULT 0.7,
    max_tokens int DEFAULT 2000,
    prompt_tokens int,
    completion_tokens int,
    total_tokens int,
    
    -- Feedback and quality signals
    feedback text, -- 'positive', 'negative', 'neutral', or null
    feedback_notes text, -- Optional feedback text
    response_quality_score float, -- Optional quality score (0-1)
    
    -- Metadata
    session_metadata jsonb DEFAULT '{}', -- Additional session context
    created_at timestamptz DEFAULT now()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_id ON public.conversation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_conversation_id ON public.conversation_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_created_at ON public.conversation_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_role ON public.conversation_logs(user_role);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_organization_id ON public.conversation_logs(organization_id) WHERE organization_id IS NOT NULL;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON public.conversation_logs TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.conversation_logs TO service_role;

-- Enable RLS
ALTER TABLE public.conversation_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own logs
CREATE POLICY "Users can read own conversation logs" ON public.conversation_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: Service role can do everything (for logging)
CREATE POLICY "Service role can manage conversation logs" ON public.conversation_logs
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- Migration 4: Add document versioning
-- ============================================
-- Add versioning columns to documents table
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS current_version INT DEFAULT 1;

ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS latest_version_id uuid;

-- Create document_versions table
CREATE TABLE IF NOT EXISTS public.document_versions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id uuid REFERENCES public.documents(id) ON DELETE CASCADE NOT NULL,
    version_number INT NOT NULL,
    storage_path text NOT NULL,
    metadata jsonb DEFAULT '{}',
    created_by uuid REFERENCES public.users(id),
    created_at timestamptz DEFAULT now(),
    UNIQUE(document_id, version_number)
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_document_versions_document_id ON public.document_versions(document_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON public.document_versions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.document_versions TO service_role;

-- Enable RLS
ALTER TABLE public.document_versions ENABLE ROW LEVEL SECURITY;

-- ============================================
-- Migration 5: Comprehensive RLS Policies
-- ============================================
-- Note: This is a large migration. See add_comprehensive_rls_policies.sql for full details
-- For now, we'll add essential policies. Run the full file separately if needed.

-- Helper function to get user role
CREATE OR REPLACE FUNCTION public.get_user_role(user_id_param uuid)
RETURNS app_role
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_role app_role;
BEGIN
    SELECT role INTO user_role
    FROM public.users
    WHERE id = user_id_param;
    
    RETURN COALESCE(user_role, 'user'::app_role);
END;
$$;

-- Helper function to check if user is admin
CREATE OR REPLACE FUNCTION public.is_admin(user_id_param uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.users
        WHERE id = user_id_param AND role = 'admin'
    );
END;
$$;

-- ============================================
-- Success Message
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ All migrations completed successfully!';
    RAISE NOTICE 'Tables created: conversation_logs, document_versions';
    RAISE NOTICE 'Functions created: search_document_chunks, get_user_role, is_admin';
    RAISE NOTICE 'Columns added: documents.status, documents.chunk_count, documents.error_message, documents.current_version, documents.latest_version_id';
END $$;

