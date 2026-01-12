# Document Versioning - Implementation Guide

## Overview

Document versioning provides complete version history, rollback capabilities, and change tracking for all documents in FounderGPT. This enables users to track changes, restore previous versions, and maintain a complete audit trail.

## Features

### ✅ Implemented

1. **Version History**
   - Automatic version tracking
   - Version numbering (1, 2, 3, ...)
   - Version metadata (notes, change summary)
   - Creation timestamps
   - Creator tracking

2. **Version Management**
   - Create new versions
   - View version history
   - Get version details
   - Compare versions

3. **Rollback Capability**
   - Rollback to any previous version
   - Preserve rollback history
   - Rollback notes and reasons

4. **Change Tracking**
   - Change summaries
   - Version notes
   - File size tracking
   - Chunk count tracking

## Database Schema

### Documents Table Additions

```sql
ALTER TABLE public.documents
ADD COLUMN version_number INT DEFAULT 1,
ADD COLUMN parent_version_id UUID REFERENCES documents(id),
ADD COLUMN is_current_version BOOLEAN DEFAULT true,
ADD COLUMN version_notes TEXT;
```

### Document Versions Table

```sql
CREATE TABLE public.document_versions (
    id uuid PRIMARY KEY,
    document_id uuid REFERENCES documents(id),
    version_number INT NOT NULL,
    storage_path text NOT NULL,
    mime_type text,
    title text NOT NULL,
    metadata jsonb,
    created_by uuid REFERENCES users(id),
    created_at timestamptz,
    version_notes text,
    change_summary text,
    file_size bigint,
    chunk_count int
);
```

## API Endpoints

### Get Version History
```
GET /api/v1/documents/{document_id}/versions
```

Returns all versions of a document:
```json
{
  "document_id": "uuid",
  "versions": [
    {
      "id": "uuid",
      "version_number": 3,
      "title": "Document Title",
      "created_at": "2024-01-01T12:00:00Z",
      "created_by": "user-uuid",
      "version_notes": "Updated with new data",
      "change_summary": "Added Q4 results",
      "is_current_version": true,
      "storage_path": "path/to/file"
    }
  ]
}
```

### Create New Version
```
POST /api/v1/documents/{document_id}/versions
Body: {
  "version_notes": "Optional notes",
  "change_summary": "What changed"
}
```

### Rollback to Version
```
POST /api/v1/documents/{document_id}/rollback
Body: {
  "target_version_number": 2,
  "rollback_notes": "Reason for rollback"
}
```

### Get Version Details
```
GET /api/v1/documents/{document_id}/versions/{version_number}
```

## Database Functions

### create_document_version()

Creates a new version of a document:
- Increments version number
- Marks old version as not current
- Creates new document record
- Records in version history

### get_document_version_history()

Retrieves complete version history:
- All versions in chain
- Version metadata
- Change summaries
- Creation info

### rollback_document_version()

Rolls back to a previous version:
- Creates new version from target
- Preserves rollback history
- Updates current version flag

## Usage

### Automatic Versioning

When uploading a new file with the same name or updating a document, a new version is automatically created.

### Manual Version Creation

```typescript
// Create a new version
await createDocumentVersion(documentId, {
    version_notes: "Updated with latest data",
    change_summary: "Added new sections"
});
```

### View Version History

```typescript
// Get all versions
const history = await getDocumentVersions(documentId);
console.log(history.versions);
```

### Rollback to Previous Version

```typescript
// Rollback to version 2
await rollbackDocumentVersion(documentId, 2, "Reverting incorrect changes");
```

## Version Chain

Documents form a version chain:
```
Document v1 (parent: null)
  └─ Document v2 (parent: v1)
      └─ Document v3 (parent: v2) [current]
```

Each version:
- References parent version
- Has unique version number
- Maintains separate storage path
- Tracks own metadata

## Access Control

- Users can view versions of documents they have access to
- Only document owners and admins can create versions
- Only document owners and admins can rollback
- RLS policies enforce access control

## Storage Considerations

### Storage Paths

Each version maintains its own storage path:
- Original: `user_id/document.pdf`
- Version 2: `user_id/document_v2.pdf`
- Version 3: `user_id/document_v3.pdf`

### Storage Cleanup

Old versions remain in storage:
- Can be archived
- Can be deleted after retention period
- Storage costs should be monitored

## Integration

### With Document Upload

When uploading a document:
1. Check if document with same name exists
2. If exists, create new version
3. If new, create version 1

### With Document Update

When updating document content:
1. Create new version
2. Update storage path
3. Process through ingestion
4. Update version history

### With RAG System

- Each version has separate chunks
- Vector search includes all versions
- Citations reference specific versions
- Version filtering in search (future)

## Best Practices

### Version Notes

Always include meaningful version notes:
- "Updated with Q4 2024 data"
- "Fixed formatting issues"
- "Added executive summary"

### Change Summaries

Provide clear change summaries:
- "Added 3 new sections"
- "Updated financial data"
- "Corrected typos and formatting"

### Rollback Strategy

- Test rollback in non-production first
- Document rollback reasons
- Verify rollback success
- Monitor after rollback

## Future Enhancements

1. **Version Comparison**
   - Diff between versions
   - Visual comparison
   - Change highlighting

2. **Version Branching**
   - Multiple version branches
   - Merge capabilities
   - Branch management

3. **Automatic Versioning**
   - Auto-version on edit
   - Scheduled versioning
   - Change detection

4. **Version Analytics**
   - Version usage stats
   - Most accessed versions
   - Version lifecycle

5. **Storage Optimization**
   - Delta storage (store only changes)
   - Compression
   - Automatic archiving

## Troubleshooting

### Version Not Created

- Check document access permissions
- Verify database function exists
- Check storage permissions
- Review error logs

### Rollback Fails

- Verify target version exists
- Check document permissions
- Ensure storage path is valid
- Review function logs

### Version History Missing

- Check RLS policies
- Verify function permissions
- Review database indexes
- Check query filters

## Security

### Access Control

- RLS policies protect version data
- Users see only accessible versions
- Admins see all versions
- Service role bypasses for operations

### Audit Trail

- All version operations logged
- Creator tracked for each version
- Timestamps for all changes
- Rollback reasons recorded

---

**Status**: ✅ Implemented and Ready
**Last Updated**: 2024-12-XX

