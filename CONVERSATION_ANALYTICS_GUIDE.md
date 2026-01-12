# Conversation Analytics & Export - Implementation Guide

## Overview

The Conversation Analytics system provides comprehensive logging, analytics, and export capabilities for all conversations in FounderGPT. This enables administrators to analyze usage patterns, audit conversations, and export training data for fine-tuning custom language models.

## Features

### ✅ Implemented

1. **Conversation Logging**
   - Automatic logging of all conversations
   - Stores user prompts, assistant responses, citations
   - Tracks retrieved chunks and documents
   - Records model parameters and token usage
   - Non-blocking logging (doesn't slow down responses)

2. **Analytics Dashboard**
   - Total conversation logs count
   - Unique users and conversations
   - Average response and prompt lengths
   - Average citations per response
   - Documents referenced statistics
   - Breakdown by user role

3. **Export Functionality**
   - JSONL export (for training data)
   - CSV export (for analysis)
   - Date range filtering
   - User-specific filtering
   - Automatic file download

4. **Admin Access**
   - Admin-only access to analytics
   - View recent conversation logs
   - Export training data
   - Filter and search capabilities

## Database Schema

### conversation_logs Table

```sql
CREATE TABLE public.conversation_logs (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES users(id),
    conversation_id uuid REFERENCES conversations(id),
    user_role app_role NOT NULL,
    organization_id text, -- For multi-tenant support
    
    -- Conversation data
    user_prompt text NOT NULL,
    assistant_response text NOT NULL,
    
    -- RAG context
    retrieved_chunks jsonb DEFAULT '[]',
    retrieved_documents jsonb DEFAULT '[]',
    citations jsonb DEFAULT '[]',
    
    -- Model info
    model_name text DEFAULT 'gpt-4',
    temperature float DEFAULT 0.7,
    max_tokens int DEFAULT 2000,
    tokens_used int,
    
    -- Feedback
    user_feedback text,
    feedback_notes text,
    response_quality_score float,
    
    -- Metadata
    session_metadata jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now()
);
```

## API Endpoints

### Get Conversation Logs
```
GET /api/v1/analytics/conversation-logs
Query Parameters:
  - user_id: Filter by user
  - conversation_id: Filter by conversation
  - start_date: ISO date string
  - end_date: ISO date string
  - limit: Number of results (1-1000)
  - offset: Pagination offset
```

### Get Analytics
```
GET /api/v1/analytics/analytics
Query Parameters:
  - start_date: ISO date string (optional)
  - end_date: ISO date string (optional)
```

Returns:
```json
{
  "total_logs": 150,
  "unique_users": 25,
  "unique_conversations": 45,
  "avg_response_length": 342.5,
  "avg_prompt_length": 89.2,
  "unique_documents_referenced": 12,
  "avg_citations_per_response": 3.2,
  "logs_by_role": {
    "admin": 10,
    "manager": 30,
    "user": 110
  }
}
```

### Export JSONL
```
GET /api/v1/analytics/export/jsonl
Query Parameters:
  - user_id: Filter by user (optional)
  - start_date: ISO date string (optional)
  - end_date: ISO date string (optional)
```

Returns: JSONL file download

### Export CSV
```
GET /api/v1/analytics/export/csv
Query Parameters:
  - user_id: Filter by user (optional)
  - start_date: ISO date string (optional)
  - end_date: ISO date string (optional)
```

Returns: CSV file download

## Usage

### Accessing Analytics

1. Log in as admin user
2. Navigate to Admin Dashboard (`/admin`)
3. Click on "Analytics" tab
4. View analytics summary and recent logs

### Exporting Training Data

1. Go to Analytics tab
2. Click "Export JSONL" or "Export CSV"
3. File downloads automatically
4. Use JSONL for fine-tuning models
5. Use CSV for data analysis

### Filtering Logs

Use query parameters in API calls:
```typescript
// Get logs for specific user
const logs = await getConversationLogs({ user_id: "user-uuid" });

// Get logs for date range
const logs = await getConversationLogs({
    start_date: "2024-01-01T00:00:00",
    end_date: "2024-12-31T23:59:59"
});
```

## Export Formats

### JSONL Format

Each line is a JSON object:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is in the document?"
    },
    {
      "role": "assistant",
      "content": "Based on the document..."
    }
  ],
  "metadata": {
    "conversation_id": "uuid",
    "user_role": "user",
    "retrieved_documents": [...],
    "citations": [...],
    "model_name": "gpt-4",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

### CSV Format

Columns:
- id
- user_id
- conversation_id
- user_role
- user_prompt (truncated to 500 chars)
- assistant_response (truncated to 500 chars)
- num_citations
- num_documents
- model_name
- created_at

## Training Data Preparation

### For Fine-Tuning

1. Export JSONL format
2. Each line contains a conversation turn
3. Format matches OpenAI fine-tuning format
4. Can be used directly with OpenAI API
5. Or converted to other formats as needed

### For Analysis

1. Export CSV format
2. Import into Excel/Google Sheets
3. Analyze patterns, trends
4. Generate reports
5. Identify common questions

## Security & Privacy

### Access Control
- Only admins can access analytics
- All endpoints require admin authentication
- RLS policies enforce user-level access

### Data Privacy
- User IDs are stored but can be anonymized
- Organization ID supports multi-tenant segmentation
- Export can filter by user for privacy

### Compliance
- Logs can be deleted per user request
- Date-based retention policies can be implemented
- Export supports GDPR compliance

## Performance

### Logging Performance
- Non-blocking logging (doesn't slow responses)
- Uses async executor for background processing
- Minimal overhead on chat responses

### Query Performance
- Indexed on user_id, conversation_id, created_at
- Efficient date range queries
- Pagination for large datasets

## Future Enhancements

1. **Advanced Analytics**:
   - Usage trends over time
   - Most common questions
   - Document popularity
   - User engagement metrics

2. **Feedback System**:
   - User feedback collection
   - Quality scoring
   - Response improvement tracking

3. **Real-time Dashboard**:
   - Live conversation monitoring
   - Real-time metrics
   - Alerts and notifications

4. **Custom Exports**:
   - Custom date ranges
   - Field selection
   - Format customization

5. **Data Retention**:
   - Automatic cleanup policies
   - Archive old logs
   - Compliance features

## Troubleshooting

### Logs Not Appearing
- Check admin role
- Verify database migration ran
- Check backend logs for errors
- Verify conversation_logger is imported

### Export Fails
- Check file size limits
- Verify date range is valid
- Check browser download settings
- Verify admin authentication

### Performance Issues
- Use pagination for large datasets
- Filter by date range
- Index database properly
- Consider archiving old logs

---

**Status**: ✅ Implemented and Ready
**Last Updated**: 2024-12-XX

