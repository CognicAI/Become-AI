"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
### removed unnecessary UUID import; site_id is int

# Request Models
class ScrapeRequest(BaseModel):
    """Request model for scraping a website."""
    site_name: str = Field(..., min_length=1, max_length=255, description="Name of the website")
    base_url: HttpUrl = Field(..., description="Base URL of the website to scrape")
    description: Optional[str] = Field(None, description="Optional description of the website")

class QueryRequest(BaseModel):
    """Request model for querying the RAG system."""
    question: str = Field(..., min_length=1, description="Question to ask about the content")
    site_base_url: HttpUrl = Field(..., description="Base URL of the site to query")
    max_chunks: Optional[int] = Field(5, ge=1, le=10, description="Maximum number of chunks to retrieve")
    llm_source: str = Field('local', description="LLM source to use: 'local' or 'cloud'")
    llm_model_name: Optional[str] = Field(None, description="Cloud LLM model name (when llm_source is 'cloud')")

# Response Models
class ScrapeResponse(BaseModel):
    """Response model for scrape initiation."""
    job_id: str = Field(..., description="Unique identifier for the scraping job")
    site_id: int = Field(..., description="Integer ID of the created site record")
    message: str = Field(..., description="Status message")
    
class ScrapeStatusResponse(BaseModel):
    """Response model for scrape job status."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current status of the job")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage")
    pages_processed: int = Field(..., ge=0, description="Number of pages processed")
    pages_total: Optional[int] = Field(None, description="Total pages to process (if known)")
    current_task: Optional[str] = Field(None, description="Current task being performed")
    error_message: Optional[str] = Field(None, description="Error message if status is 'failed'")
    started_at: datetime = Field(..., description="When the job started")
    completed_at: Optional[datetime] = Field(None, description="When the job completed")

class ChunkMetadata(BaseModel):
    """Metadata for a content chunk."""
    chunk_id: int = Field(..., description="Unique chunk identifier")
    chunk_number: int = Field(..., description="Sequential chunk number within page")
    page_url: str = Field(..., description="URL of the source page")
    page_title: str = Field(..., description="Title of the source page")
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")

class QueryResponse(BaseModel):
    """Response model for RAG queries."""
    answer: str = Field(..., description="Generated answer based on retrieved context")
    chunks_used: List[ChunkMetadata] = Field(..., description="Chunks used to generate the answer")
    processing_time: float = Field(..., description="Time taken to process the query in seconds")

# Database Models (for internal use)
class SiteCreate(BaseModel):
    """Model for creating a new site."""
    name: str
    base_url: str
    description: Optional[str] = None

class SitePageCreate(BaseModel):
    """Model for creating a new site page."""
    site_id: int
    url: str
    title: str
    summary: Optional[str]
    content: str
    metadata: Dict[str, Any] = {}

class PageChunkCreate(BaseModel):
    """Model for creating a new page chunk."""
    page_id: int
    chunk_number: int
    title: Optional[str]
    summary: Optional[str]
    content: str
    token_count: int
    embedding: List[float]  # 768-dimensional vector
    metadata: Dict[str, Any] = {}

class EmbeddingCreate(BaseModel):
    """Model for creating a new embedding."""
    chunk_id: int
    model_name: str
    embedding: List[float]  # 768-dimensional vector

# Job Tracking Models
class JobStatus(BaseModel):
    """Internal job status tracking."""
    job_id: str
    site_id: int  # integer site_id from sites.id
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: float = 0.0
    pages_processed: int = 0
    pages_total: Optional[int] = None
    current_task: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        """Pydantic config."""
        from_attributes = True