-- Revert embedding dimensions back to 1536 for text-embedding-3-small
-- This script reverts the document_chunks table back to 1536-dimensional embeddings
-- Required because HNSW index only supports up to 2000 dimensions

-- Drop the existing index first (required before altering column)
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

-- Alter the embedding column back to 1536 dimensions
ALTER TABLE public.document_chunks 
ALTER COLUMN embedding TYPE vector(1536);

-- Recreate the HNSW index with 1536 dimensions
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
ON public.document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- Update the search function to use 1536 dimensions
DROP FUNCTION IF EXISTS public.search_document_chunks(vector, float, int);
DROP FUNCTION IF EXISTS public.search_document_chunks(vector(1536), float, int);
DROP FUNCTION IF EXISTS public.search_document_chunks(vector(3072), float, int);

-- Create the function with 1536 dimensions
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
        (dc.embedding <#> query_embedding) * -1 > similarity_threshold
    ORDER BY
        dc.embedding <#> query_embedding
    LIMIT match_count;
END;
$$;

