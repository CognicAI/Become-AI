# Become AI - RAG System Copilot Instructions

This is a modular web scraping and Retrieval-Augmented Generation (RAG) system that processes website content, generates embeddings, and provides intelligent Q&A using a local LLM (Phi-3 Mini).

## Architecture Overview

This system follows a **hierarchical data pipeline**: `Sites → Pages → Chunks → Embeddings → Query Processing`

```
Sites (base_url) → Site Pages (scraped content) → Page Chunks (512 tokens) → Embeddings → RAG Queries
```

### Core Tech Stack
- **LLM**: 	phi-3-mini-128k-instruct (local via LM Studio)
- **Embedding Model**: BAAI/bge-base-en-v1.5 (768 dimensions)
- **Vector Database**: PostgreSQL with pgvector extension
- **API**: FastAPI with async support and SSE/WebSocket streaming
- **Scraping**: BeautifulSoup4/Scrapy with sitemap parsing

## Project Structure

Follow this modular organization pattern:

```
project_root/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── api/
│   │   ├── scrape.py        # Endpoints for /scrape, /status
│   │   └── query.py         # Endpoint for /query
│   ├── services/
│   │   ├── scraper.py       # Web scraping logic
│   │   ├── chunker.py       # Chunking & tokenization
│   │   ├── llm.py           # LLM summarization calls
│   │   └── embeddings.py    # Embedding generation/storage
│   ├── db/
│   │   ├── schema.sql       # Database schema
│   │   └── db.py            # Database connection and session
│   ├── models/              # Pydantic models
│   └── utils/
│       ├── logging.py
│       └── helpers.py
├── tests/
│   ├── test_scraper.py
│   └── test_query.py
├── requirements.txt
├── Dockerfile
└── .env                     # Environment variables
```

## Database Schema Architecture

The `schema.sql` defines a **4-table normalized structure**:

1. **`sites`**: Website registry (UUID primary keys, unique base_url)
2. **`site_pages`**: Scraped page content with JSONB metadata
3. **`page_chunks`**: Content segmentation (512 tokens, 50 overlap) with embeddings
4. **`embeddings`**: Optional separate vector storage for multiple models

**Vector Dimensions**: All tables use `VECTOR(768)` for BAAI/bge-base-en-v1.5 compatibility

### Key Relationships
```sql
sites(id) ←→ site_pages(site_id) ←→ page_chunks(page_id) ←→ embeddings(chunk_id)
```

## API Endpoints Design

### 1. Scraping Pipeline
```
POST /scrape
- Input: {"site_name": "...", "base_url": "https://...", "description": "..."}
- Creates site record, returns job_id
- Triggers async sitemap discovery → content extraction → chunking → embedding

GET /scrape/status/{job_id}
- Progress tracking for long-running scrape jobs
```

### 2. Query Processing
```
POST /query
- Input: {"question": "...", "site_base_url": "https://..."}
- Pipeline: Query embedding → Cosine similarity search → LLM context → Streaming response

GET /query/stream (SSE endpoint)
- Token-by-token streaming for real-time UX
```

## Development Patterns

### Chunking Strategy
- **512 tokens per chunk, 50 token overlap**
- Preserve headers (h1-h6) with content context
- Store `chunk_number` for document reconstruction
- Include `token_count` for LLM context window management

### Embedding Workflow
1. Generate embeddings using BAAI/bge-base-en-v1.5
2. Store in `page_chunks.embedding` (primary)
3. Optionally duplicate in `embeddings` table for model comparison
4. Use cosine similarity for semantic search (top 5 chunks)

### Error Handling & Resilience
- **Rate limiting**: 1 request/sec per domain
- **Timeouts**: 30s network default
- **Duplicate detection**: UNIQUE constraints on (site_id, url)
- **LLM fallbacks**: Handle failed chunk processing gracefully

### Async Processing
- Batch inserts for `site_pages` and `page_chunks`
- Connection pooling for database operations
- Background job tracking for scrape progress

## LLM Integration Specifics

### Phi-3 Mini Context Management
- Use retrieved chunks as context
- Include source citations in responses
- Stream responses token-by-token via SSE/WebSocket

### Prompt Structure
```
Context: [retrieved chunks with metadata]
Question: {user_question}
Instructions: Answer based on provided context, cite sources
```

## Frontend Integration

This is a **backend-only API service** - any frontend can consume:
- Vanilla HTML/CSS/JS
- React/Vue/Angular
- Mobile apps
- CLI tools

### SSE Streaming Example
```javascript
const evtSource = new EventSource('/query/stream?question=...');
evtSource.onmessage = (event) => {
    document.getElementById('response').innerText += event.data;
};
```

## Key Implementation Notes

### Sitemap Discovery
- Check common paths: `/sitemap.xml`, `/sitemap_index.xml`, `/sitemap/sitemap.xml`
- Handle nested sitemaps recursively
- Fallback to recursive crawling from homepage
- Always respect `robots.txt`

### Content Extraction
- Target semantic HTML: `<article>`, `<main>`, `<section>`
- Extract headers (h1-h6) for context preservation
- Skip low-value pages (login, admin, search results)
- Clean HTML while preserving text structure

### Performance Optimizations
- Cache frequently accessed embeddings
- Use async/await for I/O operations
- Implement health check endpoints
- Environment variable configuration for deployment

## Local Development Setup

### LM Studio Integration
- Ensure Phi-3 Mini is installed locally and running
- Default endpoint: `LMSTUDIO_URL=http://localhost:1234`
- Configure model name and max tokens in environment variables
- Test LLM connectivity before implementing services

### Database Initialization
```sql
-- Run schema.sql to create tables and enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;
-- Note: Requires pgcrypto for gen_random_uuid()
```

Required environment variables in `.env`:
```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dbname
LMSTUDIO_URL=http://localhost:1234
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
```

Optional: Seed `sites` table with demo site for testing

## Testing Patterns

### Scraping Pipeline Tests
- **Unit tests**: URL validation, sitemap parsing (`test_scraper.py`)
- **Content extraction**: Verify HTML cleaning preserves structure
- **Network mocking**: Rate limiting, timeouts, robots.txt handling
- **Database integration**: Test batch inserts to `site_pages` and `page_chunks`

### RAG Query Tests
- **Embedding generation**: Verify 768-dimension vectors (`test_query.py`)
- **Semantic search**: Test cosine similarity returns correct top-5 chunks
- **Full pipeline**: Question → embedding → retrieval → LLM → streaming response
- **SSE streaming**: Mock streaming responses for frontend integration

## Common Gotchas

1. **Vector Dimensions**: Ensure schema matches chosen embedding model (768 for BAAI/bge-base-en-v1.5)
2. **Token Counting**: Verify tokenizer consistency between chunking and LLM
3. **URL Normalization**: Handle trailing slashes, query params in base_url
4. **Memory Management**: Large sites require streaming/pagination
5. **CORS**: Configure for frontend integration
6. **Database Extensions**: Ensure both `vector` and `pgcrypto` extensions are enabled
7. **LM Studio Connectivity**: Test local LLM endpoint before deployment

## Deployment Readiness

- Docker containerization support
- Environment variables for all external services
- Logging levels: info, warning, error
- Health check endpoints for monitoring
- Connection pooling for database performance