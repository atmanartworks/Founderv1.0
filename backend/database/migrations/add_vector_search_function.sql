-- Migration: Add vector similarity search function
-- This improves vector search performance by using pgvector functions directly
-- Run this in Supabase SQL Editor

-- Function to search chunks with similarity threshold and permission filtering
-- Includes folder-based permissions
CREATE OR REPLACE FUNCTION search_document_chunks(
    query_embedding vector(1536),
    user_id_param uuid,
    similarity_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
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
        1 - (dc.embedding <=> query_embedding) as similarity
    FROM public.document_chunks dc
    INNER JOIN public.documents d ON dc.document_id = d.id
    LEFT JOIN public.folders f ON d.folder_id = f.id
    WHERE 
        -- Permission check: 
        -- 1. User owns the document
        -- 2. Document allows user's role or specific user
        -- 3. Document is in a folder user has access to
        (
            -- Direct document ownership
            d.owner_id = user_id_param
            OR user_id_param = ANY(d.allowed_users)
            OR EXISTS (
                SELECT 1 FROM public.users u
                WHERE u.id = user_id_param
                AND u.role = ANY(d.allowed_roles)
            )
            -- Folder-based access
            OR (
                d.folder_id IS NOT NULL
                AND (
                    f.owner_id = user_id_param
                    OR user_id_param = ANY(f.allowed_users)
                    OR EXISTS (
                        SELECT 1 FROM public.users u
                        WHERE u.id = user_id_param
                        AND u.role = ANY(f.allowed_roles)
                    )
                    OR EXISTS (
                        SELECT 1 FROM public.users u
                        WHERE u.id = user_id_param
                        AND u.role = 'admin'
                    )
                )
            )
        )
        -- Similarity threshold
        AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION search_document_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION search_document_chunks TO service_role;

