# Database Setup Instructions

## Quick Fix for Document Upload Errors

The document upload is failing because the database schema is missing the `folders` table and `folder_id` column in the `documents` table.

### Step 1: Run the Folders Migration

1. Go to **Supabase Dashboard** → Your Project → **SQL Editor**
2. Copy and paste the contents of `backend/database/add_folders_support.sql`
3. Click **Run** to execute the SQL

This will:
- Create the `folders` table (simplified, no RBAC)
- Add `folder_id` column to `documents` table
- Create necessary indexes
- Set up RLS policies

### Step 2: Verify

After running the migration, try uploading a document again. It should work now!

## What Changed

### Folders Table
- Simplified folder structure (no RBAC)
- Users can only see/manage their own folders
- Supports nested folders via `parent_id`

### Documents Table
- Added optional `folder_id` column
- Documents can now be organized in folders
- Backward compatible - existing documents work fine

## File Type Support

The system now supports:
- ✅ PDF (`.pdf`)
- ✅ DOCX (`.docx`)
- ✅ PPTX (`.pptx`) - limited support
- ✅ TXT (`.txt`)
- ✅ Markdown (`.md`)
- ✅ Other text files (fallback to text reading)

All supported files are:
1. Uploaded to Supabase Storage
2. Parsed and chunked
3. Embedded using OpenAI
4. Stored in `document_chunks` table for RAG

## Folder Creation During Upload

Users can now:
1. Select an existing folder from the dropdown
2. OR create a new folder by entering a name in "Or Create New Folder"
3. The new folder will be created automatically during upload

## Troubleshooting

If you still see errors:
1. Check that the migration ran successfully
2. Verify the `folders` table exists: `SELECT * FROM folders LIMIT 1;`
3. Verify `documents` table has `folder_id`: `SELECT column_name FROM information_schema.columns WHERE table_name = 'documents';`
4. Restart the backend after running the migration

