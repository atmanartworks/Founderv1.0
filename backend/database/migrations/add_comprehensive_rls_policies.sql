-- Migration: Comprehensive RLS Policies for FounderGPT
-- This implements row-level security based on RBAC (Role-Based Access Control)
-- Run this in Supabase SQL Editor

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get current user's role from public.users table
CREATE OR REPLACE FUNCTION public.get_user_role(user_id_param uuid)
RETURNS app_role
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
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

-- Function to check if user is admin
CREATE OR REPLACE FUNCTION public.is_admin(user_id_param uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
BEGIN
    RETURN public.get_user_role(user_id_param) = 'admin'::app_role;
END;
$$;

-- Function to check folder access
CREATE OR REPLACE FUNCTION public.has_folder_access(
    folder_id_param uuid,
    user_id_param uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    folder_record RECORD;
    user_role app_role;
BEGIN
    -- Admin has access to everything
    IF public.is_admin(user_id_param) THEN
        RETURN true;
    END IF;
    
    -- Get folder
    SELECT * INTO folder_record
    FROM public.folders
    WHERE id = folder_id_param;
    
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    
    -- Owner has access
    IF folder_record.owner_id = user_id_param THEN
        RETURN true;
    END IF;
    
    -- Get user role
    user_role := public.get_user_role(user_id_param);
    
    -- Check allowed roles
    IF user_role = ANY(folder_record.allowed_roles) THEN
        RETURN true;
    END IF;
    
    -- Check allowed users
    IF user_id_param = ANY(folder_record.allowed_users) THEN
        RETURN true;
    END IF;
    
    RETURN false;
END;
$$;

-- Function to check document access
CREATE OR REPLACE FUNCTION public.has_document_access(
    document_id_param uuid,
    user_id_param uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    doc_record RECORD;
    user_role app_role;
BEGIN
    -- Admin has access to everything
    IF public.is_admin(user_id_param) THEN
        RETURN true;
    END IF;
    
    -- Get document
    SELECT * INTO doc_record
    FROM public.documents
    WHERE id = document_id_param;
    
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    
    -- Owner has access
    IF doc_record.owner_id = user_id_param THEN
        RETURN true;
    END IF;
    
    -- Get user role
    user_role := public.get_user_role(user_id_param);
    
    -- Check document-level permissions
    IF user_id_param = ANY(doc_record.allowed_users) THEN
        RETURN true;
    END IF;
    
    IF user_role = ANY(doc_record.allowed_roles) THEN
        RETURN true;
    END IF;
    
    -- Check folder-level permissions if document is in a folder
    IF doc_record.folder_id IS NOT NULL THEN
        IF public.has_folder_access(doc_record.folder_id, user_id_param) THEN
            RETURN true;
        END IF;
    END IF;
    
    RETURN false;
END;
$$;

-- ============================================================================
-- Enable RLS on All Tables
-- ============================================================================

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Users Table Policies
-- ============================================================================

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can read own profile" ON public.users;
DROP POLICY IF EXISTS "Users can read all profiles" ON public.users;
DROP POLICY IF EXISTS "Admins can read all users" ON public.users;
DROP POLICY IF EXISTS "Admins can update users" ON public.users;

-- Users can read their own profile
CREATE POLICY "Users can read own profile" ON public.users
    FOR SELECT
    USING (auth.uid() = id);

-- Admins can read all users
CREATE POLICY "Admins can read all users" ON public.users
    FOR SELECT
    USING (public.is_admin(auth.uid()));

-- Users can update their own profile (limited fields)
CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id AND role = (SELECT role FROM public.users WHERE id = auth.uid()));

-- Admins can update any user
CREATE POLICY "Admins can update users" ON public.users
    FOR UPDATE
    USING (public.is_admin(auth.uid()))
    WITH CHECK (public.is_admin(auth.uid()));

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role full access users" ON public.users
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Folders Table Policies
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view accessible folders" ON public.folders;
DROP POLICY IF EXISTS "Users can create folders" ON public.folders;
DROP POLICY IF EXISTS "Users can update own folders" ON public.folders;
DROP POLICY IF EXISTS "Users can delete own folders" ON public.folders;
DROP POLICY IF EXISTS "Admins can manage all folders" ON public.folders;

-- Users can view folders they have access to
CREATE POLICY "Users can view accessible folders" ON public.folders
    FOR SELECT
    USING (
        public.is_admin(auth.uid()) OR
        owner_id = auth.uid() OR
        public.get_user_role(auth.uid()) = ANY(allowed_roles) OR
        auth.uid() = ANY(allowed_users)
    );

-- Users can create folders (they become owner)
CREATE POLICY "Users can create folders" ON public.folders
    FOR INSERT
    WITH CHECK (owner_id = auth.uid());

-- Users can update folders they own
CREATE POLICY "Users can update own folders" ON public.folders
    FOR UPDATE
    USING (owner_id = auth.uid())
    WITH CHECK (owner_id = auth.uid());

-- Admins can update any folder
CREATE POLICY "Admins can update all folders" ON public.folders
    FOR UPDATE
    USING (public.is_admin(auth.uid()))
    WITH CHECK (public.is_admin(auth.uid()));

-- Users can delete folders they own
CREATE POLICY "Users can delete own folders" ON public.folders
    FOR DELETE
    USING (owner_id = auth.uid());

-- Admins can delete any folder
CREATE POLICY "Admins can delete all folders" ON public.folders
    FOR DELETE
    USING (public.is_admin(auth.uid()));

-- Service role can do everything
CREATE POLICY "Service role full access folders" ON public.folders
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Documents Table Policies
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view accessible documents" ON public.documents;
DROP POLICY IF EXISTS "Users can create documents" ON public.documents;
DROP POLICY IF EXISTS "Users can update own documents" ON public.documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON public.documents;
DROP POLICY IF EXISTS "Admins can manage all documents" ON public.documents;

-- Users can view documents they have access to
CREATE POLICY "Users can view accessible documents" ON public.documents
    FOR SELECT
    USING (
        public.is_admin(auth.uid()) OR
        owner_id = auth.uid() OR
        public.get_user_role(auth.uid()) = ANY(allowed_roles) OR
        auth.uid() = ANY(allowed_users) OR
        (folder_id IS NOT NULL AND public.has_folder_access(folder_id, auth.uid()))
    );

-- Users can create documents (they become owner)
CREATE POLICY "Users can create documents" ON public.documents
    FOR INSERT
    WITH CHECK (owner_id = auth.uid());

-- Users can update documents they own
CREATE POLICY "Users can update own documents" ON public.documents
    FOR UPDATE
    USING (owner_id = auth.uid())
    WITH CHECK (owner_id = auth.uid());

-- Admins can update any document
CREATE POLICY "Admins can update all documents" ON public.documents
    FOR UPDATE
    USING (public.is_admin(auth.uid()))
    WITH CHECK (public.is_admin(auth.uid()));

-- Users can delete documents they own
CREATE POLICY "Users can delete own documents" ON public.documents
    FOR DELETE
    USING (owner_id = auth.uid());

-- Admins can delete any document
CREATE POLICY "Admins can delete all documents" ON public.documents
    FOR DELETE
    USING (public.is_admin(auth.uid()));

-- Service role can do everything
CREATE POLICY "Service role full access documents" ON public.documents
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Document Chunks Table Policies
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view accessible chunks" ON public.document_chunks;
DROP POLICY IF EXISTS "Service role full access chunks" ON public.document_chunks;

-- Users can view chunks from documents they have access to
CREATE POLICY "Users can view accessible chunks" ON public.document_chunks
    FOR SELECT
    USING (
        public.is_admin(auth.uid()) OR
        public.has_document_access(document_id, auth.uid())
    );

-- Service role can do everything (for ingestion)
CREATE POLICY "Service role full access chunks" ON public.document_chunks
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Conversations Table Policies
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own conversations" ON public.conversations;
DROP POLICY IF EXISTS "Users can create conversations" ON public.conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON public.conversations;
DROP POLICY IF EXISTS "Users can delete own conversations" ON public.conversations;
DROP POLICY IF EXISTS "Admins can view all conversations" ON public.conversations;

-- Users can view their own conversations
CREATE POLICY "Users can view own conversations" ON public.conversations
    FOR SELECT
    USING (user_id = auth.uid());

-- Admins can view all conversations
CREATE POLICY "Admins can view all conversations" ON public.conversations
    FOR SELECT
    USING (public.is_admin(auth.uid()));

-- Users can create conversations (must be their own)
CREATE POLICY "Users can create conversations" ON public.conversations
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can update their own conversations
CREATE POLICY "Users can update own conversations" ON public.conversations
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Users can delete their own conversations
CREATE POLICY "Users can delete own conversations" ON public.conversations
    FOR DELETE
    USING (user_id = auth.uid());

-- Service role can do everything
CREATE POLICY "Service role full access conversations" ON public.conversations
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Messages Table Policies
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view messages in own conversations" ON public.messages;
DROP POLICY IF EXISTS "Users can create messages in own conversations" ON public.messages;
DROP POLICY IF EXISTS "Admins can view all messages" ON public.messages;

-- Users can view messages in their own conversations
CREATE POLICY "Users can view messages in own conversations" ON public.messages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.conversations
            WHERE id = messages.conversation_id
            AND user_id = auth.uid()
        )
    );

-- Admins can view all messages
CREATE POLICY "Admins can view all messages" ON public.messages
    FOR SELECT
    USING (public.is_admin(auth.uid()));

-- Users can create messages in their own conversations
CREATE POLICY "Users can create messages in own conversations" ON public.messages
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.conversations
            WHERE id = messages.conversation_id
            AND user_id = auth.uid()
        )
    );

-- Service role can do everything
CREATE POLICY "Service role full access messages" ON public.messages
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Conversation Logs Table Policies
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can read own conversation logs" ON public.conversation_logs;
DROP POLICY IF EXISTS "Service role can manage conversation logs" ON public.conversation_logs;
DROP POLICY IF EXISTS "Admins can read all conversation logs" ON public.conversation_logs;

-- Users can read their own logs
CREATE POLICY "Users can read own conversation logs" ON public.conversation_logs
    FOR SELECT
    USING (user_id = auth.uid());

-- Admins can read all logs
CREATE POLICY "Admins can read all conversation logs" ON public.conversation_logs
    FOR SELECT
    USING (public.is_admin(auth.uid()));

-- Service role can do everything (for logging)
CREATE POLICY "Service role full access conversation logs" ON public.conversation_logs
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Audit Logs Table Policies
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can read own audit logs" ON public.audit_logs;
DROP POLICY IF EXISTS "Admins can read all audit logs" ON public.audit_logs;
DROP POLICY IF EXISTS "Service role full access audit logs" ON public.audit_logs;

-- Users can read their own audit logs
CREATE POLICY "Users can read own audit logs" ON public.audit_logs
    FOR SELECT
    USING (user_id = auth.uid());

-- Admins can read all audit logs
CREATE POLICY "Admins can read all audit logs" ON public.audit_logs
    FOR SELECT
    USING (public.is_admin(auth.uid()));

-- Service role can do everything (for logging)
CREATE POLICY "Service role full access audit logs" ON public.audit_logs
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Grant Execute Permissions
-- ============================================================================

GRANT EXECUTE ON FUNCTION public.get_user_role(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_admin(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.has_folder_access(uuid, uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.has_document_access(uuid, uuid) TO authenticated;

GRANT EXECUTE ON FUNCTION public.get_user_role(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.is_admin(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.has_folder_access(uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.has_document_access(uuid, uuid) TO service_role;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON FUNCTION public.get_user_role(uuid) IS 'Returns the role of a user from public.users table';
COMMENT ON FUNCTION public.is_admin(uuid) IS 'Returns true if user is an admin';
COMMENT ON FUNCTION public.has_folder_access(uuid, uuid) IS 'Returns true if user has access to folder (owner, role, or explicit permission)';
COMMENT ON FUNCTION public.has_document_access(uuid, uuid) IS 'Returns true if user has access to document (owner, role, explicit permission, or folder access)';

