"""Main FastAPI application entry point."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .api import scrape, query, process
from .db.db import init_db, test_connection
from .utils.logging import setup_logging
from .utils.config import settings, get_cors_origins

# Set up logging
setup_logging(level=settings.log_level)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Become AI RAG System...")
    
    # Test database connection
    if not test_connection():
        logger.error("Database connection failed!")
        logger.error("Please ensure PostgreSQL with pgvector is running and accessible.")
        logger.error("Database URL: " + settings.database_url)
        logger.error("")
        logger.error("Quick setup options:")
        logger.error("1. Install PostgreSQL locally with pgvector extension")
        logger.error("2. Use Docker: docker run --name postgres-pgvector -e POSTGRES_PASSWORD=password -p 5432:5432 -d pgvector/pgvector:pg15")
        logger.error("3. Update DATABASE_URL in .env file with correct credentials")
        raise Exception("Failed to connect to database")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    logger.info("RAG System startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG System...")

# Create FastAPI app
app = FastAPI(
    title="Become AI - RAG System",
    description="A modular web scraping and Retrieval-Augmented Generation (RAG) system",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug_mode
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Required for SSE (EventSource)
)

# Include routers
app.include_router(scrape.router)
app.include_router(query.router)
app.include_router(process.router)

@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "Become AI RAG System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "scraping": {
                "start_scrape": "POST /scrape",
                "check_status": "GET /scrape/status/{job_id}",
                "list_jobs": "GET /scrape/jobs",
                "list_sites": "GET /scrape/sites"
            },
            "query": {
                "query": "POST /query",
                "stream": "GET /query/stream",
                "similar_chunks": "GET /query/similar-chunks",
                "chunk_details": "GET /query/chunk/{chunk_id}"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db_healthy = test_connection()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": "2025-01-01T00:00:00Z"  # This would be dynamic in real implementation
        }
        
        if not db_healthy:
            raise HTTPException(status_code=503, detail=health_status)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-01-01T00:00:00Z"
            }
        )

@app.get("/config")
async def get_config():
    """Get current system configuration (non-sensitive values only)."""
    return {
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "max_chunks_per_query": settings.max_chunks_per_query,
        "scraping_rate_limit": settings.scraping_rate_limit,
        "scraping_timeout": settings.scraping_timeout,
        "lm_model_name": settings.lm_model_name,
        "lm_max_tokens": settings.lm_max_tokens,
        "lm_temperature": settings.lm_temperature,
        "debug_mode": settings.debug_mode
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug_mode,
        log_level=settings.log_level.lower()
    )