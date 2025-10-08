# Become AI - RAG System

A modular web scraping and Retrieval-Augmented Generation (RAG) system that processes website content, generates embeddings, and provides intelligent Q&A using a local LLM (Phi-3 Mini).

## Architecture Overview

This system follows a **hierarchical data pipeline**: `Sites → Pages → Chunks → Embeddings → Query Processing`

```
Sites (base_url) → Site Pages (scraped content) → Page Chunks (512 tokens) → Embeddings → RAG Queries
```

## Tech Stack

- **LLM**: Phi-3 Mini (local via LM Studio)
- **Embedding Model**: BAAI/bge-base-en-v1.5 (768 dimensions)
- **Vector Database**: PostgreSQL with pgvector extension
- **API**: FastAPI with async support and SSE streaming
- **Scraping**: BeautifulSoup4/Scrapy with sitemap parsing

## Quick Start

### Prerequisites

1. **PostgreSQL with pgvector extension**
2. **LM Studio** running locally with Phi-3 Mini model
3. **Python 3.11+**

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd become-ai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
# Create database and run schema.sql
createdb become_ai
psql -d become_ai -f app/db/schema.sql
```

5. Start the application:
```bash
uvicorn app.main:app --reload
```

### Docker Setup

```bash
# Start with Docker Compose (includes PostgreSQL)
docker-compose up -d

# Or build manually
docker build -t become-ai-rag .
docker run -p 8000:8000 become-ai-rag
```

## API Usage

### Scraping a Website

```bash
# Start scraping
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "site_name": "Example Site",
    "base_url": "https://example.com",
    "description": "Example website for testing"
  }'

# Check status
curl "http://localhost:8000/scrape/status/{job_id}"
```

### Querying Content

```bash
# Regular query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this website about?",
    "site_base_url": "https://example.com"
  }'

# Streaming query (SSE)
curl "http://localhost:8000/query/stream?question=What+is+this+about&site_base_url=https://example.com"
```

## Development

### Project Structure

```
project_root/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── api/
│   │   ├── scrape.py        # Scraping endpoints
│   │   └── query.py         # Query endpoints
│   ├── services/
│   │   ├── scraper.py       # Web scraping logic
│   │   ├── chunker.py       # Content chunking
│   │   ├── llm.py           # LLM integration
│   │   └── embeddings.py    # Embedding generation
│   ├── db/
│   │   ├── schema.sql       # Database schema
│   │   └── db.py            # Database connection
│   ├── models/              # Pydantic models
│   └── utils/               # Utilities and config
├── tests/                   # Test suite
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Running Tests

```bash
pytest tests/
```

### Key Features

- **Sitemap Discovery**: Automatically finds and parses sitemaps
- **Intelligent Content Extraction**: Focuses on main content areas
- **Hierarchical Chunking**: 512 tokens with 50-token overlap
- **Vector Similarity Search**: Cosine similarity with pgvector
- **Streaming Responses**: Real-time SSE for better UX
- **Rate Limiting**: Respectful scraping with robots.txt compliance

### Configuration

Key environment variables in `.env`:

```bash
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/become_ai
LMSTUDIO_URL=http://localhost:1234
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## License

MIT License - see LICENSE file for details.