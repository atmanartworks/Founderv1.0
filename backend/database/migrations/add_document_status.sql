-- Migration: Add status and chunk_count to documents table
-- Run this in Supabase SQL Editor if these columns don't exist

-- Add status column (processing, completed, failed)
ALTER TABLE public.documents 
ADD COLUMN IF NOT EXISTS status text DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed'));

-- Add chunk_count column
ALTER TABLE public.documents 
ADD COLUMN IF NOT EXISTS chunk_count integer DEFAULT 0;

-- Add error_message column for failed documents
ALTER TABLE public.documents 
ADD COLUMN IF NOT EXISTS error_message text;

-- Create index on status for faster queries
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);

-- Create index on owner_id for faster user document queries
CREATE INDEX IF NOT EXISTS idx_documents_owner_id ON public.documents(owner_id);

-- Create index on folder_id for faster folder queries
CREATE INDEX IF NOT EXISTS idx_documents_folder_id ON public.documents(folder_id);

