# Parent-Document Retrieval Implementation

## Overview

Parent-Document Retrieval is an advanced RAG technique that improves context quality by separating **search precision** from **context richness**.

### The Problem

Traditional RAG systems face a tradeoff:
- **Small chunks**: Better semantic search accuracy, but lack context
- **Large chunks**: Better context, but lower search precision

### The Solution

Parent-Document Retrieval uses a hierarchical approach:
1. **Child chunks** (small, ~400 tokens): Used for precise semantic search
2. **Parent chunks** (large, ~2000 tokens): Retrieved for rich context

When a query matches a child chunk, the system returns its parent chunk to the LLM, providing better context while maintaining search accuracy.

## Architecture

```
Document
    ├── Parent Chunk 1 (2000 tokens)
    │   ├── Child Chunk 1.1 (400 tokens) [indexed with embedding]
    │   ├── Child Chunk 1.2 (400 tokens) [indexed with embedding]
    │   └── Child Chunk 1.3 (400 tokens) [indexed with embedding]
    ├── Parent Chunk 2 (2000 tokens)
    │   ├── Child Chunk 2.1 (400 tokens) [indexed with embedding]
    │   └── Child Chunk 2.2 (400 tokens) [indexed with embedding]
    └── ...
```

### Database Schema

The implementation extends the `document_chunks` table:

```sql
CREATE TABLE document_chunks (
    chunk_id UUID PRIMARY KEY,
    doc_id UUID REFERENCES documents(doc_id),
    content TEXT NOT NULL,
    embedding vector(1536),  -- Only on child chunks
    
    -- Parent-Document Retrieval fields
    parent_chunk_id UUID REFERENCES document_chunks(chunk_id),
    is_parent BOOLEAN DEFAULT FALSE,
    chunk_type VARCHAR(20) DEFAULT 'child',  -- 'parent' or 'child'
    
    metadata JSONB
);
```

### Retrieval Flow

1. **Indexing**:
   - Documents are split into parent chunks (2000 tokens, 200 overlap)
   - Each parent is further split into child chunks (400 tokens, 50 overlap)
   - Only child chunks receive embeddings
   - Parent-child relationships are stored in the database

2. **Querying**:
   - Hybrid search (vector + keyword) runs on child chunks
   - Matching child chunks are identified
   - System retrieves parent chunks instead of child chunks
   - Parents are deduplicated and ranked by best child score

## Usage

### 1. Ingest Documents with Hierarchical Chunking

```python
from sentinel_rag.core.engine import SentinelEngine
from sentinel_rag.services.database import DatabaseManager

db = DatabaseManager()
engine = SentinelEngine(db=db)

# Enable hierarchical chunking (default)
doc_id = engine.ingest_documents(
    source="path/to/document.pdf",
    title="Enterprise Security Policy",
    description="Company-wide security guidelines",
    user_id="user-uuid",
    department_id="dept-uuid",
    classification="confidential",
    use_hierarchical=True  # Enable Parent-Document Retrieval
)
```

### 2. Query with Parent Retrieval

```python
# Query with parent retrieval (default)
results = engine.query(
    question="What are the password requirements?",
    user_id="user-uuid",
    k=5,
    use_parent_retrieval=True  # Return parent chunks
)

# Each result will contain:
# - content: Full parent chunk text (rich context)
# - metadata.retrieval_type: "parent"
# - metadata.score: RRF score from matching child chunk
```

### 3. Compare with Traditional Retrieval

```python
# Traditional flat chunking
doc_id = engine.ingest_documents(
    source="path/to/document.pdf",
    title="Document Title",
    description="Description",
    user_id="user-uuid",
    department_id="dept-uuid",
    classification="public",
    use_hierarchical=False  # Traditional chunking
)

# Query without parent retrieval
results = engine.query(
    question="Your question here",
    user_id="user-uuid",
    k=5,
    use_parent_retrieval=False  # Direct chunk retrieval
)
```

## Configuration

### Chunk Size Tuning

Adjust chunk sizes based on your use case:

```python
# In document_processor.py
chunk_data = self.doc_processor.hierarchical_chunks(
    doc_content,
    parent_chunk_size=2000,   # Larger for more context
    parent_overlap=200,       # ~10% overlap
    child_chunk_size=400,     # Smaller for precision
    child_overlap=50          # ~12.5% overlap
)
```

### Recommendations by Document Type

| Document Type | Parent Size | Child Size | Rationale |
|---------------|-------------|------------|-----------|
| Technical Docs | 2500 | 500 | Need more context for technical concepts |
| Legal Contracts | 3000 | 400 | Long clauses require larger parents |
| News Articles | 1500 | 300 | Shorter, more focused content |
| FAQs | 1000 | 200 | Questions are self-contained |

## Performance Considerations

### Storage Impact

- **Increase**: ~3-4x storage compared to flat chunking
  - Parent chunks: Not indexed (no embeddings)
  - Child chunks: Fully indexed with embeddings
- **Tradeoff**: Better retrieval quality vs. more storage

### Query Performance

- **Search**: Runs on child chunks (smaller index, faster)
- **Retrieval**: Single join to fetch parent chunks
- **Indexes**: Added `idx_document_chunks_parent_id` for efficient parent lookup

### Memory Optimization

The implementation optimizes memory by:
1. Only embedding child chunks (not parents)
2. Using efficient PostgreSQL joins
3. Deduplicating parent chunks in SQL

## Hybrid Search Integration

Parent-Document Retrieval works seamlessly with hybrid search:

```sql
-- Searches child chunks with hybrid search (vector + keyword)
-- Returns deduplicated parent chunks with aggregated scores
WITH vector_search AS (
    SELECT chunk_id, rank FROM document_chunks
    WHERE chunk_type = 'child' AND embedding <=> query_vector < threshold
),
keyword_search AS (
    SELECT chunk_id, rank FROM document_chunks
    WHERE chunk_type = 'child' AND searchable_text_tsvector @@ query
),
matched_children AS (
    SELECT parent_chunk_id, MAX(rrf_score) as score
    FROM document_chunks
    JOIN vector_search USING (chunk_id)
    JOIN keyword_search USING (chunk_id)
    GROUP BY parent_chunk_id
)
SELECT parent_chunks.* FROM matched_children
JOIN document_chunks parent_chunks ON matched_children.parent_chunk_id = parent_chunks.chunk_id
ORDER BY score DESC;
```

## RBAC Compatibility

Parent-Document Retrieval preserves all RBAC controls:
- Child chunks inherit department/classification from parent document
- Access filters apply during child chunk search
- No security boundaries crossed during parent retrieval

## Migration Guide

### Migrating Existing Data

To migrate existing flat chunks to hierarchical structure:

```python
# 1. Re-ingest documents with hierarchical chunking enabled
# 2. Drop old chunks after verification

# The schema supports both strategies simultaneously:
# - Old documents: chunk_type = NULL (backward compatible)
# - New documents: chunk_type = 'parent' or 'child'
```

### Backward Compatibility

The implementation maintains backward compatibility:
- `use_parent_retrieval=False` works with both old and new chunks
- Existing queries continue to work without modification
- Schema changes are additive (new columns with defaults)

## Monitoring & Debugging

### Check Chunk Distribution

```sql
-- Count parent vs child chunks
SELECT 
    chunk_type, 
    COUNT(*) as count,
    AVG(LENGTH(content)) as avg_length
FROM document_chunks
GROUP BY chunk_type;
```

### Verify Parent-Child Relationships

```sql
-- Check orphaned chunks
SELECT COUNT(*) FROM document_chunks
WHERE chunk_type = 'child' AND parent_chunk_id IS NULL;

-- Check average children per parent
SELECT AVG(child_count) FROM (
    SELECT parent_chunk_id, COUNT(*) as child_count
    FROM document_chunks
    WHERE chunk_type = 'child'
    GROUP BY parent_chunk_id
) subquery;
```

### Query Performance Analysis

```python
# Add to metadata for analysis
metadata = {
    "retrieval_type": "parent",
    "matched_child_count": 3,  # How many children matched
    "parent_length": 2143,      # Parent chunk size
    "score": 0.8542             # Aggregated RRF score
}
```

## Benefits

### 1. Better Context Quality
- Parent chunks provide complete paragraphs/sections
- Reduced context fragmentation
- Better LLM understanding

### 2. Improved Search Precision
- Child chunks are smaller and more focused
- Embeddings capture fine-grained semantics
- Less noise in search results

### 3. Reduced Hallucinations
- More context reduces LLM guessing
- Complete thoughts reduce misinterpretation
- Better source attribution

### 4. Flexible Optimization
- Tune parent/child sizes independently
- Balance precision vs. context per use case
- A/B test different configurations

## Limitations

1. **Storage**: Requires more database space
2. **Complexity**: More complex than flat chunking
3. **Tuning**: Requires experimentation to find optimal sizes
4. **Processing**: Slightly slower ingestion due to hierarchical splitting

## Best Practices

1. **Start with defaults**: Use 2000/400 token split initially
2. **Monitor metrics**: Track retrieval quality and adjust
3. **Use metadata**: Store chunk statistics for analysis
4. **Test with real queries**: Evaluate on your actual use cases
5. **Consider document structure**: Respect natural boundaries (sections, paragraphs)

## Advanced: Custom Splitters

For specialized documents, customize the hierarchical splitter:

```python
def hierarchical_chunks_custom(self, markdown_text: str):
    # Custom parent splitter - by sections
    parent_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "H1"), ("##", "H2")]
    )
    parents = parent_splitter.split_text(markdown_text)
    
    # Custom child splitter - by paragraphs
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        separators=["\n\n", "\n", ". ", " "]
    )
    
    # Build hierarchy...
```
