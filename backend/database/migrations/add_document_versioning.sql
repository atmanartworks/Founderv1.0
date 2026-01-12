-- Migration: Add Document Versioning Support
-- This enables version history, rollback, and change tracking for documents

-- Add versioning columns to documents table
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS version_number INT DEFAULT 1 NOT NULL,
ADD COLUMN IF NOT EXISTS parent_version_id UUID REFERENCES public.documents(id),
ADD COLUMN IF NOT EXISTS is_current_version BOOLEAN DEFAULT true NOT NULL,
ADD COLUMN IF NOT EXISTS version_notes TEXT;

-- Create document_versions table for version history
CREATE TABLE IF NOT EXISTS public.document_versions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id uuid REFERENCES public.documents(id) ON DELETE CASCADE NOT NULL,
    version_number INT NOT NULL,
    
    -- Version metadata
    storage_path text NOT NULL,
    mime_type text,
    title text NOT NULL,
    metadata jsonb DEFAULT '{}',
    
    -- Version info
    created_by uuid REFERENCES public.users(id),
    created_at timestamptz DEFAULT now(),
    version_notes text,
    
    -- Change tracking
    change_summary text,
    file_size bigint,
    chunk_count int DEFAULT 0,
    
    -- Constraints
    UNIQUE(document_id, version_number)
);

-- Create index for efficient version queries
CREATE INDEX idx_document_versions_document_id ON public.document_versions(document_id);
CREATE INDEX idx_document_versions_version_number ON public.document_versions(document_id, version_number);
CREATE INDEX idx_documents_parent_version ON public.documents(parent_version_id);
CREATE INDEX idx_documents_is_current_version ON public.documents(is_current_version);

-- Function to create new version
CREATE OR REPLACE FUNCTION public.create_document_version(
    p_document_id uuid,
    p_storage_path text,
    p_title text,
    p_mime_type text,
    p_metadata jsonb,
    p_created_by uuid,
    p_version_notes text DEFAULT NULL,
    p_change_summary text DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
    v_new_version_id uuid;
    v_new_version_number int;
    v_current_doc RECORD;
BEGIN
    -- Get current document info
    SELECT * INTO v_current_doc
    FROM public.documents
    WHERE id = p_document_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Document not found';
    END IF;
    
    -- Calculate new version number
    SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_new_version_number
    FROM public.documents
    WHERE id = p_document_id OR parent_version_id = p_document_id;
    
    -- Mark old version as not current
    UPDATE public.documents
    SET is_current_version = false
    WHERE id = p_document_id;
    
    -- Create new document record (new version)
    INSERT INTO public.documents (
        id,
        folder_id,
        owner_id,
        title,
        storage_path,
        mime_type,
        metadata,
        allowed_roles,
        allowed_users,
        version_number,
        parent_version_id,
        is_current_version,
        version_notes,
        status,
        created_at
    )
    VALUES (
        gen_random_uuid(),
        v_current_doc.folder_id,
        v_current_doc.owner_id,
        p_title,
        p_storage_path,
        p_mime_type,
        p_metadata,
        v_current_doc.allowed_roles,
        v_current_doc.allowed_users,
        v_new_version_number,
        p_document_id,
        true,
        p_version_notes,
        'processing',
        now()
    )
    RETURNING id INTO v_new_version_id;
    
    -- Create version history record
    INSERT INTO public.document_versions (
        document_id,
        version_number,
        storage_path,
        mime_type,
        title,
        metadata,
        created_by,
        version_notes,
        change_summary
    )
    VALUES (
        v_new_version_id,
        v_new_version_number,
        p_storage_path,
        p_mime_type,
        p_title,
        p_metadata,
        p_created_by,
        p_version_notes,
        p_change_summary
    );
    
    -- Also record old version in history
    INSERT INTO public.document_versions (
        document_id,
        version_number,
        storage_path,
        mime_type,
        title,
        metadata,
        created_by,
        version_notes,
        change_summary
    )
    VALUES (
        p_document_id,
        v_current_doc.version_number,
        v_current_doc.storage_path,
        v_current_doc.mime_type,
        v_current_doc.title,
        v_current_doc.metadata,
        v_current_doc.owner_id::uuid,
        v_current_doc.version_notes,
        'Previous version'
    )
    ON CONFLICT (document_id, version_number) DO NOTHING;
    
    RETURN v_new_version_id;
END;
$$;

-- Function to get version history
CREATE OR REPLACE FUNCTION public.get_document_version_history(
    p_document_id uuid
)
RETURNS TABLE (
    id uuid,
    version_number int,
    title text,
    created_at timestamptz,
    created_by uuid,
    version_notes text,
    change_summary text,
    is_current_version boolean,
    storage_path text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH version_tree AS (
        -- Get all versions in the chain
        SELECT d.id, d.version_number, d.title, d.created_at, d.owner_id as created_by,
               d.version_notes, d.is_current_version, d.storage_path, d.parent_version_id
        FROM public.documents d
        WHERE d.id = p_document_id OR d.parent_version_id = p_document_id
           OR d.id IN (SELECT parent_version_id FROM public.documents WHERE id = p_document_id)
        
        UNION
        
        SELECT d.id, d.version_number, d.title, d.created_at, d.owner_id as created_by,
               d.version_notes, d.is_current_version, d.storage_path, d.parent_version_id
        FROM public.documents d
        WHERE d.parent_version_id IN (
            SELECT id FROM public.documents 
            WHERE id = p_document_id OR parent_version_id = p_document_id
        )
    )
    SELECT 
        vt.id,
        vt.version_number,
        vt.title,
        vt.created_at,
        vt.created_by,
        vt.version_notes,
        COALESCE(dv.change_summary, '') as change_summary,
        vt.is_current_version,
        vt.storage_path
    FROM version_tree vt
    LEFT JOIN public.document_versions dv ON dv.document_id = vt.id AND dv.version_number = vt.version_number
    ORDER BY vt.version_number DESC;
END;
$$;

-- Function to rollback to previous version
CREATE OR REPLACE FUNCTION public.rollback_document_version(
    p_document_id uuid,
    p_target_version_number int,
    p_rollback_by uuid,
    p_rollback_notes text DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
    v_target_doc RECORD;
    v_new_version_id uuid;
    v_new_version_number int;
BEGIN
    -- Find target version
    SELECT * INTO v_target_doc
    FROM public.documents
    WHERE (id = p_document_id OR parent_version_id = p_document_id)
      AND version_number = p_target_version_number;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Version % not found for document', p_target_version_number;
    END IF;
    
    -- Get current document
    DECLARE
        v_current_doc RECORD;
    BEGIN
        SELECT * INTO v_current_doc
        FROM public.documents
        WHERE (id = p_document_id OR parent_version_id = p_document_id)
          AND is_current_version = true;
    END;
    
    -- Calculate new version number
    SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_new_version_number
    FROM public.documents
    WHERE id = p_document_id OR parent_version_id = p_document_id;
    
    -- Mark current version as not current
    UPDATE public.documents
    SET is_current_version = false
    WHERE id = v_current_doc.id;
    
    -- Create rollback version (restore from target)
    INSERT INTO public.documents (
        id,
        folder_id,
        owner_id,
        title,
        storage_path,
        mime_type,
        metadata,
        allowed_roles,
        allowed_users,
        version_number,
        parent_version_id,
        is_current_version,
        version_notes,
        status,
        created_at
    )
    VALUES (
        gen_random_uuid(),
        v_current_doc.folder_id,
        v_current_doc.owner_id,
        v_target_doc.title,
        v_target_doc.storage_path,
        v_target_doc.mime_type,
        v_target_doc.metadata,
        v_current_doc.allowed_roles,
        v_current_doc.allowed_users,
        v_new_version_number,
        v_current_doc.id,
        true,
        COALESCE(p_rollback_notes, 'Rollback to version ' || p_target_version_number),
        'processing',
        now()
    )
    RETURNING id INTO v_new_version_id;
    
    -- Record in version history
    INSERT INTO public.document_versions (
        document_id,
        version_number,
        storage_path,
        mime_type,
        title,
        metadata,
        created_by,
        version_notes,
        change_summary
    )
    VALUES (
        v_new_version_id,
        v_new_version_number,
        v_target_doc.storage_path,
        v_target_doc.mime_type,
        v_target_doc.title,
        v_target_doc.metadata,
        p_rollback_by,
        COALESCE(p_rollback_notes, 'Rollback to version ' || p_target_version_number),
        'Rollback to version ' || p_target_version_number
    );
    
    RETURN v_new_version_id;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.create_document_version TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_document_version_history TO authenticated;
GRANT EXECUTE ON FUNCTION public.rollback_document_version TO authenticated;

GRANT EXECUTE ON FUNCTION public.create_document_version TO service_role;
GRANT EXECUTE ON FUNCTION public.get_document_version_history TO service_role;
GRANT EXECUTE ON FUNCTION public.rollback_document_version TO service_role;

-- Enable RLS on document_versions
ALTER TABLE public.document_versions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view versions of documents they have access to
CREATE POLICY "Users can view accessible document versions" ON public.document_versions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_versions.document_id
            AND (
                d.owner_id = auth.uid() OR
                public.is_admin(auth.uid()) OR
                public.has_document_access(d.id, auth.uid())
            )
        )
    );

-- Policy: Service role can do everything
CREATE POLICY "Service role full access document versions" ON public.document_versions
    FOR ALL
    USING (auth.role() = 'service_role');

-- Comments
COMMENT ON TABLE public.document_versions IS 'Stores version history for documents';
COMMENT ON COLUMN public.documents.version_number IS 'Version number of this document';
COMMENT ON COLUMN public.documents.parent_version_id IS 'Reference to parent version';
COMMENT ON COLUMN public.documents.is_current_version IS 'True if this is the current version';
COMMENT ON COLUMN public.documents.version_notes IS 'Notes about this version';

