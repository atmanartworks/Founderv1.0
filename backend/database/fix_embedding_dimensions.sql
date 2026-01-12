-- Fix embedding dimensions to support text-embedding-3-large (3072 dimensions)
-- This script updates the document_chunks table to support 3072-dimensional embeddings

-- Drop the existing index first (required before altering column)
-- Note: The index name might be auto-generated, so we'll drop all indexes on embedding column
DO $$
DECLARE
    idx_record RECORD;
BEGIN
    FOR idx_record IN 
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'document_chunks' 
        AND indexdef LIKE '%embedding%'
    LOOP
        EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(idx_record.indexname);
    END LOOP;
END $$;

-- Alter the embedding column to support 3072 dimensions
ALTER TABLE public.document_chunks 
ALTER COLUMN embedding TYPE vector(3072);

-- Recreate the index with the new dimension
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
ON public.document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- Also update the search function to support 3072 dimensions
-- Drop the old function first (if it exists)
DROP FUNCTION IF EXISTS public.search_document_chunks(vector, float, int);
DROP FUNCTION IF EXISTS public.search_document_chunks(vector(1536), float, int);
DROP FUNCTION IF EXISTS public.search_document_chunks(vector(3072), float, int);

-- Create the function with 3072 dimensions
CREATE OR REPLACE FUNCTION public.search_document_chunks(
    query_embedding vector(3072),
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
        (dc.embedding <#> query_embedding) * -1 > similarity_threshold
    ORDER BY
        dc.embedding <#> query_embedding
    LIMIT match_count;
END;
$$;

