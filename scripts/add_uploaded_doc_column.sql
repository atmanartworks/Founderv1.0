-- Add uploaded_document column to messages table if it breaks persistence
ALTER TABLE messages ADD COLUMN IF NOT EXISTS uploaded_document JSONB;
