# Become AI RAG System - Setup Guide

## 🎯 Prerequisites

### 1. PostgreSQL with pgvector
Install PostgreSQL and the pgvector extension:

**Windows (using chocolatey):**
```bash
choco install postgresql
# Download and install pgvector from: https://github.com/pgvector/pgvector/releases
```

**Or use Docker:**
```bash
docker run --name postgres-pgvector -e POSTGRES_PASSWORD=password -p 5432:5432 -d pgvector/pgvector:pg15
```

### 2. LM Studio
1. Download LM Studio from: https://lmstudio.ai/
2. Install and open LM Studio
3. Download the Phi-3 Mini model:
   - Go to "Discover" tab
   - Search for "microsoft/Phi-3-mini-4k-instruct"
   - Download the model
4. Start a local server:
   - Go to "Developer" tab
   - Click "Start Server"
   - Note the server URL (usually http://localhost:1234)

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd become-ai

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Install dependencies (already done if you followed the installation)
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Create .env file from template
copy .env.example .env  # Windows
# or
cp .env.example .env  # Linux/Mac

# Edit .env file with your settings
```

**Key settings to update in `.env`:**
```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/become_ai
LMSTUDIO_URL=http://localhost:1234
```

### 3. Setup Database
```sql
-- Connect to PostgreSQL and create database
CREATE DATABASE become_ai;

-- Connect to the new database and run schema
\c become_ai
\i app/db/schema.sql

-- Or using psql command line:
psql -U postgres -d become_ai -f app/db/schema.sql
```

### 4. Test the System
```bash
# Run component tests
python test_components.py

# Start the server
python start.py
```

### 5. Verify Installation
Open your browser and go to:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📖 Usage Examples

### Scrape a Website
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "site_name": "Example Documentation",
    "base_url": "https://docs.example.com",
    "description": "Example website documentation"
  }'
```

### Check Scraping Status
```bash
curl "http://localhost:8000/scrape/status/{job_id}"
```

### Query the RAG System
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I get started?",
    "site_base_url": "https://docs.example.com"
  }'
```

### Stream Responses (SSE)
```bash
curl "http://localhost:8000/query/stream?question=What+is+this+about&site_base_url=https://docs.example.com"
```

## 🐳 Docker Setup

### Using Docker Compose (Recommended)
```bash
# Start the entire stack (PostgreSQL + API)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the stack
docker-compose down
```

### Manual Docker Build
```bash
# Build the image
docker build -t become-ai-rag .

# Run with external PostgreSQL
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+psycopg2://user:password@host.docker.internal:5432/become_ai \
  -e LMSTUDIO_URL=http://host.docker.internal:1234 \
  become-ai-rag
```

## 🔧 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure virtual environment is activated
.venv\Scripts\activate

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

**2. Database Connection Failed**
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure pgvector extension is installed

**3. LM Studio Connection Failed**
- Start LM Studio local server
- Verify LMSTUDIO_URL in .env
- Check if Phi-3 Mini model is loaded

**4. Embedding Model Download Issues**
```bash
# Manually download model (first run will be slow)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5')"
```

### Performance Tips

**1. GPU Acceleration**
- Install CUDA-enabled PyTorch for faster embeddings
- Configure LM Studio to use GPU

**2. Database Optimization**
```sql
-- Create index for better vector search performance
CREATE INDEX ON page_chunks USING ivfflat (embedding vector_cosine_ops);
```

**3. Memory Management**
- Adjust chunk size based on available memory
- Use batch processing for large websites

## 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│   Content        │───▶│   Embedding     │
│   (Sitemap +    │    │   Chunker        │    │   Service       │
│   Beautiful     │    │   (512 tokens)   │    │   (BGE-base)    │
│   Soup)         │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   Vector         │    │   LLM Service   │
│   (Sites,       │◀───│   Search         │◀───│   (Phi-3 Mini  │
│   Pages,        │    │   (Cosine        │    │   via LM        │
│   Chunks)       │    │   Similarity)    │    │   Studio)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI REST API                            │
│              (Async + SSE Streaming Support)                   │
└─────────────────────────────────────────────────────────────────┘
```

## 📞 Support

For issues and questions:
1. Check the logs: `docker-compose logs` or application output
2. Verify all prerequisites are installed and running
3. Test individual components with `python test_components.py`
4. Review the API documentation at `/docs`

## 🔄 Development

To modify the system:
1. Make changes to the code
2. Run tests: `python test_components.py`
3. Test API endpoints with the interactive docs
4. Deploy using Docker or direct Python execution

The system is designed to be modular and extensible - you can easily add new embedding models, LLM providers, or scraping capabilities by extending the service classes.