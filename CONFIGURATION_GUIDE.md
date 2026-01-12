# Configuration Guide - FounderGPT

## Required vs Optional API Keys

### Required Keys ✅

1. **OpenAI API Key** - **MANDATORY**
   ```
   OPENAI_API_KEY=sk-...
   ```
   - Used for: LLM (GPT-4), Embeddings
   - Without this: System will not work

2. **Supabase Keys** - **MANDATORY**
   ```
   SUPABASE_URL=https://...
   SUPABASE_KEY=eyJ...
   SUPABASE_SERVICE_ROLE_KEY=eyJ...
   ```
   - Used for: Database, Storage, Authentication
   - Without this: System will not work

### Optional Keys ⚠️

1. **Llama Cloud API Key** - **OPTIONAL**
   ```
   LLAMA_CLOUD_API_KEY=llx-...
   ```
   - Used for: Advanced document parsing (Llama Parse)
   - **Fallback**: If not provided, uses basic PDFReader/DocxReader
   - **Recommendation**: 
     - ✅ Use if you have complex documents (tables, images, layouts)
     - ✅ Use if you need better extraction quality
     - ❌ Skip if you only have simple text documents
     - ❌ Skip if you want to reduce API costs

## RAG Configuration for Large Documents

### Current Configuration (Optimized for Large Documents)

```env
# For 50-page documents with 10,000+ words:

# Number of chunks to retrieve per query
RAG_CHUNK_LIMIT=10  # Increased from 5 for better coverage

# Chunk size (characters)
CHUNK_SIZE=2048  # Increased from 1024 for better context

# Chunk overlap (characters)
CHUNK_OVERLAP=200  # Increased from 20 for better continuity

# Similarity threshold (0-1)
SIMILARITY_THRESHOLD=0.7  # Good balance
```

### Why These Settings?

**For 50-page documents (10,000+ words):**

1. **CHUNK_SIZE=2048**:
   - ✅ Better context per chunk
   - ✅ Fewer chunks to manage (better performance)
   - ✅ More complete information per chunk
   - ⚠️ Slightly higher embedding costs

2. **CHUNK_OVERLAP=200**:
   - ✅ Prevents information loss at chunk boundaries
   - ✅ Better continuity for long documents
   - ✅ Important for sentences that span chunks

3. **RAG_CHUNK_LIMIT=10**:
   - ✅ Retrieves more relevant chunks
   - ✅ Better coverage for large documents
   - ✅ More context for GPT-4 to generate answers
   - ⚠️ Slightly higher token usage

### Configuration Recommendations by Document Size

#### Small Documents (< 10 pages, < 2,000 words)
```env
RAG_CHUNK_LIMIT=5
CHUNK_SIZE=1024
CHUNK_OVERLAP=100
SIMILARITY_THRESHOLD=0.75
```

#### Medium Documents (10-30 pages, 2,000-6,000 words)
```env
RAG_CHUNK_LIMIT=7
CHUNK_SIZE=1536
CHUNK_OVERLAP=150
SIMILARITY_THRESHOLD=0.7
```

#### Large Documents (30-100 pages, 6,000-20,000 words) ✅ **Recommended for your case**
```env
RAG_CHUNK_LIMIT=10
CHUNK_SIZE=2048
CHUNK_OVERLAP=200
SIMILARITY_THRESHOLD=0.7
```

#### Very Large Documents (100+ pages, 20,000+ words)
```env
RAG_CHUNK_LIMIT=15
CHUNK_SIZE=3072
CHUNK_OVERLAP=300
SIMILARITY_THRESHOLD=0.65
```

## Embedding Model Selection

### text-embedding-3-small (Default)
- ✅ Fast and cost-effective
- ✅ Good for most use cases
- ✅ 1536 dimensions
- **Cost**: ~$0.02 per 1M tokens

### text-embedding-3-large (Your Current Setting)
- ✅ Better accuracy
- ✅ Better for complex queries
- ✅ 3072 dimensions
- ⚠️ Higher cost (~$0.13 per 1M tokens)
- **Recommendation**: Good for large documents

### text-embedding-ada-002 (Legacy)
- ⚠️ Older model
- ⚠️ Lower performance
- ✅ Lower cost
- **Not recommended** for new projects

## Cost Considerations

### Embedding Costs (per 1M tokens)

For a 50-page document (~10,000 words ≈ 13,000 tokens):

- **text-embedding-3-small**: ~$0.00026 per document
- **text-embedding-3-large**: ~$0.00169 per document

### LLM Costs (GPT-4)

- Input: ~$30 per 1M tokens
- Output: ~$60 per 1M tokens
- With RAG_CHUNK_LIMIT=10: ~$0.01-0.05 per query

### Llama Parse Costs (if used)

- ~$0.003 per page
- 50-page document: ~$0.15
- **One-time cost** per document

## Performance Optimization

### For Large Documents

1. **Increase CHUNK_SIZE**:
   - Reduces number of chunks
   - Faster embedding generation
   - Better context per chunk

2. **Increase CHUNK_OVERLAP**:
   - Prevents information loss
   - Better for long documents
   - Minimal performance impact

3. **Adjust RAG_CHUNK_LIMIT**:
   - Balance between coverage and cost
   - More chunks = better answers but higher cost
   - Test with your queries to find optimal value

4. **Use text-embedding-3-large**:
   - Better semantic understanding
   - Worth the extra cost for large documents

## Testing Your Configuration

### Test Query Performance

1. Upload a 50-page document
2. Ask complex questions
3. Check response quality
4. Monitor token usage
5. Adjust settings as needed

### Monitor These Metrics

- **Response Quality**: Are answers complete?
- **Citation Accuracy**: Are citations relevant?
- **Response Time**: Is it fast enough?
- **Token Usage**: Is cost acceptable?

## Recommended Configuration for Your Use Case

Based on your requirements (50 pages, 10,000+ words):

```env
# OpenAI
OPENAI_API_KEY=sk-...  # REQUIRED
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-3-large  # Good choice

# Llama Parse (OPTIONAL - can skip)
# LLAMA_CLOUD_API_KEY=llx-...  # Comment out if not using

# RAG Configuration (Optimized for large documents)
RAG_CHUNK_LIMIT=10
CHUNK_SIZE=2048
CHUNK_OVERLAP=200
SIMILARITY_THRESHOLD=0.7

# Feature Flags
ENABLE_LLAMA_PARSE=false  # Set to false if not using Llama Parse
```

## Fallback Behavior

### Without Llama Parse

The system will:
1. ✅ Use basic PDFReader for PDFs
2. ✅ Use DocxReader for DOCX files
3. ✅ Still extract text and create chunks
4. ✅ Still generate embeddings
5. ✅ Still work for RAG queries

**Limitations without Llama Parse**:
- ⚠️ May miss complex layouts
- ⚠️ May not extract tables perfectly
- ⚠️ May not preserve page numbers accurately
- ✅ Still functional for most documents

## Summary

### Your Questions Answered

1. **Is LLAMA_CLOUD_API_KEY mandatory?**
   - ❌ **NO** - It's optional
   - ✅ System works with just OpenAI API key
   - ✅ Falls back to basic readers if not provided

2. **Will current config handle 50-page documents?**
   - ✅ **YES** - With the optimized settings above
   - ✅ CHUNK_SIZE=2048 is good for large documents
   - ✅ RAG_CHUNK_LIMIT=10 provides good coverage
   - ✅ CHUNK_OVERLAP=200 prevents information loss

### Recommended Action

1. **Keep OpenAI keys** (required)
2. **Skip Llama Parse** if you want to reduce costs (optional)
3. **Use optimized RAG settings** for large documents (see above)
4. **Test with your documents** and adjust as needed

---

**Status**: ✅ Configuration Optimized
**Last Updated**: 2024-12-XX

