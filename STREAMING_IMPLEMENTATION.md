# Streaming Responses Implementation

## Overview

FounderGPT now supports **real-time streaming responses** using Server-Sent Events (SSE). This provides a ChatGPT-like experience where users see responses appear word-by-word as they're generated.

## How It Works

### Backend (FastAPI)

1. **Streaming Endpoint**: `/api/v1/chat/query` with `stream: true` parameter
2. **Server-Sent Events (SSE)**: Uses FastAPI's `StreamingResponse` with `text/event-stream` media type
3. **OpenAI Streaming**: Uses OpenAI's streaming API to get tokens as they're generated
4. **Event Types**:
   - `citations`: Sent first with all citation metadata
   - `content`: Streamed chunks of text content
   - `done`: Final signal with complete answer
   - `error`: Error messages if something goes wrong

### Frontend (Next.js)

1. **EventSource Alternative**: Uses `fetch` with `ReadableStream` API (more flexible than EventSource)
2. **Real-time Updates**: Updates message content as chunks arrive
3. **Citation Handling**: Receives citations early and displays them
4. **Fallback**: Falls back to non-streaming if streaming fails

## Usage

### Enable Streaming

Streaming is **enabled by default**. To disable:

```typescript
// In chat/page.tsx
const useStreaming = false; // Disable streaming
```

Or set in environment:
```env
ENABLE_STREAMING=false
```

### API Request

**Streaming Request:**
```typescript
POST /api/v1/chat/query
{
  "query": "What is in the document?",
  "conversation_id": "uuid-optional",
  "stream": true
}
```

**Response (SSE Stream):**
```
data: {"type":"citations","citations":[...]}

data: {"type":"content","content":"Based"}

data: {"type":"content","content":" on"}

data: {"type":"content","content":" the"}

data: {"type":"done","full_answer":"Based on the document..."}
```

### Non-Streaming Request

**Request:**
```typescript
POST /api/v1/chat/query
{
  "query": "What is in the document?",
  "conversation_id": "uuid-optional",
  "stream": false
}
```

**Response:**
```json
{
  "answer": "Complete answer text...",
  "citations": [...]
}
```

## Implementation Details

### Backend Streaming Flow

```python
# 1. Check if streaming requested
if request.stream and settings.ENABLE_STREAMING:
    return StreamingResponse(stream_chat_response(...))

# 2. Stream generator function
async def stream_chat_response(...):
    # Get chunks from vector search
    chunks = await search_chunks(...)
    
    # Send citations first
    yield f"data: {json.dumps({'type': 'citations', ...})}\n\n"
    
    # Stream OpenAI response
    stream = client.chat.completions.create(..., stream=True)
    for chunk in stream:
        yield f"data: {json.dumps({'type': 'content', ...})}\n\n"
    
    # Send completion
    yield f"data: {json.dumps({'type': 'done', ...})}\n\n"
```

### Frontend Streaming Flow

```typescript
// 1. Create fetch request
const response = await fetch(`${API_URL}/chat/query`, {
    method: "POST",
    body: JSON.stringify({ query, stream: true })
});

// 2. Get reader
const reader = response.body?.getReader();
const decoder = new TextDecoder();

// 3. Read stream
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    // Parse SSE data
    const data = JSON.parse(line.slice(6));
    
    if (data.type === "content") {
        // Append to message content
        message.content += data.content;
    }
}
```

## Event Types

### `citations`
Sent first with all citation metadata:
```json
{
  "type": "citations",
  "citations": [
    {
      "chunk_id": "uuid",
      "label": "[1]",
      "content": "Text preview...",
      "document_id": "uuid",
      "document_title": "Document Name",
      "page_number": 3,
      "start_char_idx": 1500,
      "end_char_idx": 1800,
      "metadata": {...}
    }
  ]
}
```

### `content`
Streamed text chunks:
```json
{
  "type": "content",
  "content": " word"
}
```

### `done`
Final signal with complete answer:
```json
{
  "type": "done",
  "full_answer": "Complete answer text..."
}
```

### `error`
Error message:
```json
{
  "type": "error",
  "content": "Error message"
}
```

## Benefits

1. **Better UX**: Users see responses immediately
2. **Perceived Performance**: Feels faster even if total time is same
3. **Progressive Loading**: Citations appear early
4. **Error Handling**: Can show errors immediately

## Configuration

### Backend

```python
# app/core/config.py
ENABLE_STREAMING: bool = True  # Enable/disable streaming
```

### Frontend

```typescript
// In chat/page.tsx
const useStreaming = true;  // Enable/disable streaming
```

## Testing

### Manual Testing

1. Open chat interface
2. Ask a question
3. Watch response appear word-by-word
4. Verify citations appear early
5. Check that complete message is saved

### Browser DevTools

1. Open Network tab
2. Find `/chat/query` request
3. Check `Response` tab shows streaming data
4. Verify `Content-Type: text/event-stream`

## Troubleshooting

### Streaming Not Working

1. **Check backend logs**: Look for streaming errors
2. **Verify ENABLE_STREAMING**: Check config is `true`
3. **Check browser console**: Look for fetch/stream errors
4. **Test with curl**:
   ```bash
   curl -N -H "Authorization: Bearer TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"query":"test","stream":true}' \
        http://localhost:8000/api/v1/chat/query
   ```

### Response Appears All at Once

- Streaming might be disabled
- Check `stream: true` in request
- Verify `ENABLE_STREAMING` is `true`
- Check network tab for streaming response

### Citations Not Appearing

- Check citations are sent in stream
- Verify frontend handles `citations` event type
- Check browser console for parsing errors

## Performance Considerations

1. **Network**: Streaming uses more connections but feels faster
2. **Server**: Minimal overhead, just streaming instead of buffering
3. **Client**: Slightly more CPU for parsing, but better UX
4. **Bandwidth**: Same total data, just sent incrementally

## Future Enhancements

1. **Typing Indicators**: Show when AI is thinking
2. **Cancel Stream**: Allow users to cancel mid-stream
3. **Streaming Citations**: Stream citations as they're found
4. **Multi-turn Streaming**: Stream in conversation context
5. **Rate Limiting**: Per-user streaming limits

---

**Status**: ✅ Implemented and Ready
**Last Updated**: 2024-12-XX

