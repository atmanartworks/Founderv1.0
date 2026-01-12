-- ============================================
-- SAFE FIX: Create conversation_logs table (Idempotent)
-- ============================================
-- This version safely handles existing objects
-- Copy and paste this entire script into Supabase SQL Editor
-- ============================================

-- Create table if it doesn't exist
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
    tokens_used int, -- Total tokens consumed (from OpenAI usage.total_tokens)
    
    -- Feedback and quality signals
    feedback text, -- 'positive', 'negative', 'neutral', or null
    feedback_notes text, -- Optional feedback text
    response_quality_score float, -- Optional quality score (0-1)
    
    -- Metadata
    session_metadata jsonb DEFAULT '{}', -- Additional session context
    created_at timestamptz DEFAULT now()
);

-- Create indexes (IF NOT EXISTS is safe)
CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_id ON public.conversation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_conversation_id ON public.conversation_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_created_at ON public.conversation_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_role ON public.conversation_logs(user_role);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_organization_id ON public.conversation_logs(organization_id) WHERE organization_id IS NOT NULL;

-- Grant permissions (idempotent)
GRANT SELECT, INSERT, UPDATE ON public.conversation_logs TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.conversation_logs TO service_role;

-- Enable RLS
ALTER TABLE public.conversation_logs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Users can read own conversation logs" ON public.conversation_logs;
DROP POLICY IF EXISTS "Service role can manage conversation logs" ON public.conversation_logs;

-- Create policies
CREATE POLICY "Users can read own conversation logs" ON public.conversation_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage conversation logs" ON public.conversation_logs
    FOR ALL USING (auth.role() = 'service_role');

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ conversation_logs table created/updated successfully!';
END $$;

