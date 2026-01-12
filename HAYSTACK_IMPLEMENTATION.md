# Haystack RAG Implementation

## Overview

The RAG system has been migrated from a custom implementation to **Haystack AI**, a production-grade framework for building LLM applications. This provides better modularity, extensibility, and maintainability.

## What Changed

### Before (Custom Implementation)
- Custom vector search logic
- Manual embedding generation
- Direct OpenAI API calls
- Custom prompt building

### After (Haystack Implementation)
- **Haystack Pipelines**: Modular, composable RAG pipelines
- **Custom Supabase Document Store**: Integrates with existing pgvector database
- **Custom Supabase Retriever**: RBAC-aware retrieval component
- **Haystack Components**: Embedders, generators, prompt builders

## Architecture

### Components

1. **`SupabaseDocumentStore`** (`backend/app/services/haystack_store.py`)
   - Custom Haystack Document Store interface
   - Integrates with Supabase `document_chunks` table
   - Enforces RBAC (Role-Based Access Control)
   - Supports filtering by user permissions

2. **`SupabaseRetriever`** (`backend/app/services/haystack_rag.py`)
   - Custom Haystack retriever component
   - Uses Supabase RPC function for efficient vector search
   - Falls back to Python-based similarity search if needed
   - Respects user permissions and folder access

3. **`HaystackRAGService`** (`backend/app/services/haystack_rag.py`)
   - Main RAG service using Haystack pipelines
   - Handles both streaming and non-streaming responses
   - Maintains citation support
   - Integrates with conversation logging

4. **`ChatService`** (`backend/app/services/chat.py`)
   - Simplified wrapper that delegates to Haystack RAG service
   - Maintains same API for backward compatibility

## Benefits

### 1. **Modularity**
- Components can be swapped independently
- Easy to add new features (e.g., reranking, query expansion)
- Clear separation of concerns

### 2. **Extensibility**
- Easy to add new retrievers (e.g., hybrid search, keyword + semantic)
- Can add preprocessing/postprocessing steps
- Supports custom components

### 3. **Maintainability**
- Well-documented framework
- Active community support
- Standard patterns and best practices

### 4. **Technology Agnostic**
- Can switch embedding models easily
- Can swap LLM providers
- Can change document stores

## Features Preserved

✅ **RBAC (Role-Based Access Control)**
- User permissions enforced at retrieval level
- Folder-based access control
- Document-level permissions

✅ **Citations**
- Character offsets for highlighting
- Page numbers
- Document metadata

✅ **Streaming Responses**
- Real-time token streaming
- Early citation delivery

✅ **Conversation Logging**
- Analytics integration
- Training data export

## Files Created/Modified

### New Files
- `backend/app/services/haystack_store.py` - Custom document store
- `backend/app/services/haystack_rag.py` - Haystack RAG service

### Modified Files
- `backend/app/services/chat.py` - Now delegates to Haystack
- `backend/requirements.txt` - Added `haystack-ai`

## Usage

The API remains the same - no changes needed in frontend or API endpoints:

```python
# Still works the same way
chat_service = ChatService()
response = await chat_service.generate_response(query, user, conversation_id)
```

## Configuration

Haystack uses the same configuration from `settings`:
- `OPENAI_API_KEY` - For embeddings and LLM
- `OPENAI_MODEL` - LLM model (gpt-4o)
- `OPENAI_EMBEDDING_MODEL` - Embedding model
- `RAG_CHUNK_LIMIT` - Number of chunks to retrieve
- `SIMILARITY_THRESHOLD` - Minimum similarity score

## Future Enhancements

With Haystack, you can easily add:

1. **Hybrid Search**: Combine keyword and semantic search
2. **Reranking**: Use cross-encoders to improve retrieval quality
3. **Query Expansion**: Expand queries with synonyms/related terms
4. **Multi-step Reasoning**: Complex query decomposition
5. **Answer Extraction**: Extract precise answers from documents
6. **Document Classification**: Route queries to specialized pipelines

## Testing

To test the implementation:

1. Start the backend: `cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload`
2. Send a chat query through the API
3. Verify responses include citations
4. Check that RBAC is enforced (users only see their documents)

## Migration Notes

- **Backward Compatible**: All existing API endpoints work unchanged
- **No Database Changes**: Uses existing `document_chunks` table
- **No Frontend Changes**: Same response format
- **Performance**: Should be similar or better (uses same Supabase RPC function)

## Troubleshooting

If you encounter issues:

1. **Import Errors**: Ensure `haystack-ai` is installed: `pip install haystack-ai`
2. **API Key Errors**: Check that `OPENAI_API_KEY` is set in `.env`
3. **Retrieval Issues**: Verify Supabase RPC function `search_document_chunks` exists
4. **RBAC Issues**: Check that user permissions are correctly set in database

## Resources

- [Haystack Documentation](https://docs.haystack.deepset.ai/)
- [Haystack GitHub](https://github.com/deepset-ai/haystack)
- [Haystack Cookbook](https://github.com/deepset-ai/haystack-cookbook)

---

**Status**: ✅ Implemented and Integrated
**Date**: 2024-12-XX
**Version**: Haystack 2.21.0

