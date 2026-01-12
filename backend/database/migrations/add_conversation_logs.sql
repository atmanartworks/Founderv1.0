-- Migration: Add conversation logs table for analytics and training data
-- This table stores structured conversation data for analytics, auditing, and model training

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
    tokens_used int, -- If available from OpenAI response
    
    -- Feedback and quality signals
    user_feedback text, -- 'positive', 'negative', 'neutral', or null
    feedback_notes text, -- Optional feedback text
    response_quality_score float, -- Optional quality score (0-1)
    
    -- Metadata
    session_metadata jsonb DEFAULT '{}', -- Additional session context
    created_at timestamptz DEFAULT now()
);

-- Indexes for efficient querying
CREATE INDEX idx_conversation_logs_user_id ON public.conversation_logs(user_id);
CREATE INDEX idx_conversation_logs_conversation_id ON public.conversation_logs(conversation_id);
CREATE INDEX idx_conversation_logs_created_at ON public.conversation_logs(created_at);
CREATE INDEX idx_conversation_logs_user_role ON public.conversation_logs(user_role);
CREATE INDEX idx_conversation_logs_organization_id ON public.conversation_logs(organization_id) WHERE organization_id IS NOT NULL;

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

-- Policy: Admins can read all logs
-- Note: This requires a function to check admin role
-- For now, admins will use service role or we'll add a function later

COMMENT ON TABLE public.conversation_logs IS 'Stores conversation logs for analytics, auditing, and training data export';
COMMENT ON COLUMN public.conversation_logs.retrieved_chunks IS 'Array of chunk objects: {chunk_id, content, similarity, document_id}';
COMMENT ON COLUMN public.conversation_logs.retrieved_documents IS 'Array of document objects: {document_id, title, folder_id}';
COMMENT ON COLUMN public.conversation_logs.citations IS 'Citation objects from assistant response';
COMMENT ON COLUMN public.conversation_logs.session_metadata IS 'Additional context: browser, device, session_id, etc.';

