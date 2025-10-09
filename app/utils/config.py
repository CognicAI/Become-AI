"""Configuration management for the RAG system."""
# pyright: reportCallIssue=false
# pyright: reportGeneralTypeIssues=false
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database settings
    database_url: str = Field(
        default="postgresql+psycopg2://user:password@localhost:5432/become_ai",
        env="DATABASE_URL",
        description="PostgreSQL database connection URL"
    )
    
    # LM Studio settings
    lmstudio_url: str = Field(
        default="http://localhost:1234",
        env="LMSTUDIO_URL", 
        description="LM Studio API endpoint URL"
    )
    
    lm_model_name: str = Field(
        default="phi-3-mini-128k-instruct",
        env="LM_MODEL_NAME",
        description="LLM model name for Phi-3 Mini"
    )
    
    lm_max_tokens: int = Field(
        default=2048,
        env="LM_MAX_TOKENS",
        description="Maximum tokens for LLM responses"
    )
    
    lm_temperature: float = Field(
        default=0.7,
        env="LM_TEMPERATURE", 
        description="Temperature for LLM responses"
    )
    
    # Embedding settings
    embedding_model: str = Field(
        default="BAAI/bge-base-en-v1.5",
        env="EMBEDDING_MODEL",
        description="HuggingFace embedding model name"
    )
    
    embedding_dimension: int = Field(
        default=768,
        env="EMBEDDING_DIMENSION",
        description="Dimension of embedding vectors"
    )
    
    # Scraping settings
    scraping_rate_limit: float = Field(
        default=1.0,
        env="SCRAPING_RATE_LIMIT",
        description="Rate limit for scraping (requests per second)"
    )
    
    scraping_timeout: int = Field(
        default=30,
        env="SCRAPING_TIMEOUT",
        description="HTTP timeout for scraping requests in seconds"
    )
    
    scraping_user_agent: str = Field(
        default="BecomeAI-RAG-Bot/1.0 (+https://github.com/becomeai/rag-system)",
        env="SCRAPING_USER_AGENT",
        description="User agent string for web scraping"
    )
    # Test mode configuration for scraping: limit URLs in test mode
    scraping_test_mode: bool = Field(
        default=False,
        env="SCRAPING_TEST_MODE",
        description="Enable test mode to limit number of pages scraped"
    )
    scraping_test_url_limit: int = Field(
        default=5,
        env="SCRAPING_TEST_URL_LIMIT",
        description="Maximum number of URLs to scrape in test mode"
    )
    
    # Chunking settings
    chunk_size: int = Field(
        default=400,
        env="CHUNK_SIZE",
        description="Size of text chunks in tokens"
    )
    
    chunk_overlap: int = Field(
        default=50,
        env="CHUNK_OVERLAP",
        description="Overlap between consecutive chunks in tokens"
    )
    
    # Query settings
    max_chunks_per_query: int = Field(
        default=5,
        env="MAX_CHUNKS_PER_QUERY",
        description="Maximum number of chunks to retrieve for each query"
    )
    
    # API settings
    api_host: str = Field(
        default="0.0.0.0",
        env="API_HOST",
        description="Host for the FastAPI server"
    )
    
    api_port: int = Field(
        default=8000,
        env="API_PORT",
        description="Port for the FastAPI server"
    )
    
    api_cors_origins: str = Field(
        default="*",
        env="API_CORS_ORIGINS",
        description="Comma-separated list of CORS origins"
    )
    
    # Logging settings
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # Development settings
    debug_mode: bool = Field(
        default=False,
        env="DEBUG_MODE",
        description="Enable debug mode"
    )
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()

def get_cors_origins():
    """Get CORS origins as a list."""
    if settings.api_cors_origins == "*":
        return ["*"]
    return [origin.strip() for origin in settings.api_cors_origins.split(",")]