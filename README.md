# Become AI - RAG System

![Become AI RAG System](Gemini_Generated_Image_7o373f7o373f7o37.png)

A modular web scraping and Retrieval-Augmented Generation (RAG) system that processes website content, generates embeddings, and provides intelligent Q&A using local LLMs via LM Studio.

## Architecture Overview

This system follows a **hierarchical data pipeline**: `Sites → Pages → Chunks → Embeddings → Metadata → Query Processing`

```
Sites (base_url) → Site Pages (scraped content) → Page Chunks (512 tokens) → Embeddings + Metadata → RAG Queries
```

## Tech Stack

- **LLM**: Qwen 2.5 3B Instruct (local via LM Studio)
- **Embedding Model**: text-embedding-bge-base-en-v1.5 (768 dimensions)
- **Vector Database**: PostgreSQL 16+ with pgvector extension
- **API**: FastAPI with async support and SSE streaming
- **Scraping**: BeautifulSoup4 with sitemap parsing

## Quick Start

### Prerequisites

1. **PostgreSQL 16+** with pgvector extension
2. **LM Studio** running locally with models loaded:
   - Chat model: `qwen2.5-3b-instruct`
   - Embedding model: `text-embedding-bge-base-en-v1.5`
3. **Python 3.12+**

### Installation

#### Linux/macOS

1. Clone the repository:
```bash
git clone <repository-url>
cd Become-AI
```

2. Run the start script (handles everything automatically):
```bash
python start.py
```

The script will:
- Create a virtual environment
- Install all dependencies
- Copy `.env.example` to `.env`
- Start the FastAPI server

#### Manual Installation

1. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
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
# Create database and user
sudo -u postgres psql -c "CREATE USER harshajustin WITH PASSWORD '0909';"
sudo -u postgres psql -c "CREATE DATABASE anurag OWNER harshajustin;"
sudo -u postgres psql -d anurag -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

5. Start the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Usage

### 1. Scraping a Website

```bash
# Start scraping
curl -X POST "http://localhost:8000/scrape/" \
  -H "Content-Type: application/json" \
  -d '{
    "site_name": "Example Site",
    "base_url": "https://example.com",
    "description": "Example website for testing"
  }'

# Check status
curl "http://localhost:8000/scrape/status/{job_id}"
```

### 2. Generate Metadata (Titles & Summaries)

After scraping, generate AI-powered titles and summaries for all content:

```bash
# Process specific number of pages (synchronous, returns results)
curl -X POST "http://localhost:8000/process/generate-metadata?site_id=1&limit=5"

# Process all pages (background task)
curl -X POST "http://localhost:8000/process/generate-metadata?site_id=1"
```

The metadata generation:
- Processes only unprocessed chunks (`is_metadata_updated = FALSE`)
- Generates titles and summaries for each chunk
- Aggregates chunk summaries into page-level metadata
- Handles errors gracefully (failed chunks remain unprocessed for retry)
- Uses batch processing (3 pages at a time) to avoid database connection exhaustion

### 3. Querying Content

```bash
# Regular query
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this website about?",
    "site_base_url": "https://example.com"
  }'

# Streaming query (SSE)
curl "http://localhost:8000/query/stream?question=What+is+this+about&site_base_url=https://example.com&max_chunks=5"
```

## Development

### Project Structure

```
Become-AI/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── api/
│   │   ├── scrape.py        # Scraping endpoints
│   │   ├── query.py         # Query endpoints
│   │   └── process.py       # Metadata generation endpoints
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
├── start.py                 # Cross-platform startup script
├── requirements.txt
└── .env.example
```

### Key Features

- **Sitemap Discovery**: Automatically finds and parses sitemaps
- **Intelligent Content Extraction**: Focuses on main content areas
- **Hierarchical Chunking**: 512 tokens with 50-token overlap
- **Hierarchical Metadata**: AI-generated titles/summaries at chunk and page levels
- **Vector Similarity Search**: Cosine similarity with pgvector
- **Streaming Responses**: Real-time SSE for better UX
- **Rate Limiting**: Respectful scraping with robots.txt compliance
- **Batch Processing**: Prevents database connection pool exhaustion
- **Error Recovery**: Failed operations don't mark content as processed

### Configuration

Key environment variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql+psycopg2://harshajustin:0909@localhost:5432/anurag

# LM Studio
LMSTUDIO_URL=http://localhost:1234
LM_MODEL_NAME=qwen2.5-3b-instruct
EMBEDDING_MODEL=text-embedding-bge-base-en-v1.5

# LLM Settings
LM_MAX_TOKENS=2048
LM_TEMPERATURE=0.7

# Embedding Settings
EMBEDDING_DIMENSION=768

# Chunking
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Troubleshooting

### Database Connection Pool Exhaustion
If you see `QueuePool limit of size 5 overflow 10 reached` errors:
- The system now uses batch processing (3 pages at a time)
- Adjust `batch_size` in `app/api/process.py` if needed

### LLM Session Closed Errors
If metadata generation fails with "Session is closed":
- Check that LM Studio is running
- Verify both models are loaded in LM Studio
- Failed chunks will be retried on next run (not marked as processed)

### PostgreSQL Setup on Linux
```bash
# Install PostgreSQL and pgvector
sudo apt install postgresql-16 postgresql-16-pgvector

# Configure PostgreSQL to listen on TCP
sudo nano /etc/postgresql/16/main/postgresql.conf
# Set: listen_addresses = '*'

# Reload PostgreSQL
sudo systemctl reload postgresql
```

## License

MIT License - see LICENSE file for details.