"""API endpoints for web scraping operations."""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from ..db.db import get_db
from ..models import ScrapeRequest, ScrapeResponse, ScrapeStatusResponse, JobStatus
from ..services.scraper import WebScraper
from ..services.chunker import ContentChunker
from ..services.embeddings import embedding_service
from ..services.llm import llm_service
from ..utils.helpers import generate_job_id, normalize_url, get_current_timestamp
from ..utils.config import settings

logger = logging.getLogger(__name__)
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from ..db.db import get_db
from ..models import ScrapeRequest, ScrapeResponse, ScrapeStatusResponse, JobStatus
from ..services.scraper import WebScraper
from ..services.chunker import ContentChunker
from ..services.embeddings import embedding_service
from ..services.llm import llm_service
from ..utils.helpers import generate_job_id, normalize_url, get_current_timestamp
from ..utils.config import settings

logger = logging.getLogger(__name__)

# Router for scraping endpoints
router = APIRouter(prefix="/scrape", tags=["scraping"])

# In-memory job tracking (in production, use Redis or database)
job_tracker: Dict[str, JobStatus] = {}

async def scrape_site_background(
    job_id: str, 
    site_id: uuid.UUID, 
    base_url: str, 
    site_name: str,
    description: Optional[str]
):
    """Background task for scraping a website.
    
    Args:
        job_id: Unique job identifier
        site_id: UUID of the site record
        base_url: Base URL to scrape
        site_name: Name of the site
        description: Optional site description
    """
    try:
        # Update job status
        job_tracker[job_id].status = "processing"
        job_tracker[job_id].current_task = "Initializing scraping"
        
        # Initialize services
        await embedding_service.initialize()
        
        # Test LLM connection
        async with llm_service as llm:
            if not await llm.test_connection():
                raise Exception("Failed to connect to LM Studio")
        
        chunker = ContentChunker()
        
        # Start scraping
        job_tracker[job_id].current_task = "Discovering pages"
        
        async with WebScraper() as scraper:
            # Scrape the site
            scraped_pages = await scraper.scrape_site(base_url, max_pages=1000)
            
            if not scraped_pages:
                raise Exception("No pages were successfully scraped")
            
            job_tracker[job_id].pages_total = len(scraped_pages)
            job_tracker[job_id].current_task = "Processing pages"
            
            # Process pages in database
            from ..db.db import SessionLocal
            db = SessionLocal()
            
            try:
                for i, page in enumerate(scraped_pages):
                    # Insert page into database
                    page_query = text("""
                        INSERT INTO site_pages (site_id, url, title, summary, content, metadata, scraped_at)
                        VALUES (:site_id, :url, :title, :summary, :content, :metadata, :scraped_at)
                        RETURNING id
                    """)
                    
                    # Convert metadata dict to JSON string for PostgreSQL JSONB
                    import json
                    metadata_json = json.dumps(page.metadata) if page.metadata else '{}'
                    
                    page_result = db.execute(page_query, {
                        'site_id': str(site_id),
                        'url': page.url,
                        'title': page.title,
                        'summary': page.summary,
                        'content': page.content,
                        'metadata': metadata_json,
                        'scraped_at': get_current_timestamp()
                    })
                    
                    page_row = page_result.fetchone()
                    if page_row:
                        page_id = page_row[0]
                    else:
                        logger.error(f"Failed to insert page: {page.url}")
                        continue
                    
                    # Update progress
                    job_tracker[job_id].pages_processed = i + 1
                    job_tracker[job_id].progress = (i + 1) / len(scraped_pages) * 50  # 50% for scraping
                    job_tracker[job_id].current_task = f"Processing page {i+1}/{len(scraped_pages)}: {page.title[:50]}..."
                    
                    # Chunk the page content
                    chunks = chunker.chunk_page_content(
                        url=page.url,
                        title=page.title,
                        content=page.content,
                        headers=page.headers,
                        page_metadata=page.metadata
                    )
                    
                    if chunks:
                        # Generate and store embeddings for chunks
                        chunk_ids = await embedding_service.store_chunk_embeddings(chunks, str(page_id))
                        logger.info(f"Stored {len(chunk_ids)} chunks with embeddings for page: {page.title}")
                        
                        # Note: LLM enhancement disabled for now to focus on core functionality
                        # TODO: Re-enable LLM chunk enhancement after testing core features
                                    except Exception as e:
                                        logger.warning(f"Failed to generate chunk title: {e}")
                                
                                if not chunk.summary:
                                    try:
                                        chunk.summary = await llm.generate_chunk_summary(chunk.content, chunk.title)
                                    except Exception as e:
                                        logger.warning(f"Failed to generate chunk summary: {e}")
                                
                                # Insert chunk into database
                                chunk_query = text("""
                                    INSERT INTO page_chunks 
                                    (page_id, chunk_number, title, summary, content, token_count, embedding, metadata, created_at)
                                    VALUES (:page_id, :chunk_number, :title, :summary, :content, :token_count, :embedding, :metadata, :created_at)
                                """)
                                
                                db.execute(chunk_query, {
                                    'page_id': page_id,
                                    'chunk_number': chunk.chunk_number,
                                    'title': chunk.title,
                                    'summary': chunk.summary,
                                    'content': chunk.content,
                                    'token_count': chunk.token_count,
                                    'embedding': embedding_result.embedding,
                                    'metadata': chunk.metadata,
                                    'created_at': get_current_timestamp()
                                })
                    
                    # Update progress for chunk processing
                    job_tracker[job_id].progress = 50 + (i + 1) / len(scraped_pages) * 50  # Second 50% for processing
                    
                    # Commit after each page to avoid losing progress
                    db.commit()
                
                # Final completion
                job_tracker[job_id].status = "completed"
                job_tracker[job_id].progress = 100.0
                job_tracker[job_id].current_task = "Completed successfully"
                job_tracker[job_id].completed_at = get_current_timestamp()
                
                logger.info(f"Scraping job {job_id} completed successfully")
                
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
                
    except Exception as e:
        logger.error(f"Scraping job {job_id} failed: {e}")
        job_tracker[job_id].status = "failed"
        job_tracker[job_id].error_message = str(e)
        job_tracker[job_id].completed_at = get_current_timestamp()

@router.post("/", response_model=ScrapeResponse)
async def start_scraping(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start scraping a website.
    
    Args:
        request: Scraping request with site details
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        ScrapeResponse with job ID and site ID
    """
    try:
        # Normalize URL
        base_url = normalize_url(str(request.base_url))
        
        # Check if site already exists
        existing_site = db.execute(
            text("SELECT id FROM sites WHERE base_url = :url"),
            {'url': base_url}
        ).fetchone()
        
        if existing_site:
            raise HTTPException(
                status_code=400,
                detail=f"Site {base_url} has already been scraped. Site ID: {existing_site[0]}"
            )
        
        # Create site record
        site_query = text("""
            INSERT INTO sites (name, base_url, description, created_at)
            VALUES (:name, :base_url, :description, :created_at)
            RETURNING id
        """)
        
        result = db.execute(site_query, {
            'name': request.site_name,
            'base_url': base_url,
            'description': request.description,
            'created_at': get_current_timestamp()
        })
        
        site_row = result.fetchone()
        if site_row:
            site_id = site_row[0]
        else:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create site record")
            
        db.commit()
        
        # Generate job ID
        job_id = generate_job_id(base_url)
        
        # Initialize job tracking
        job_tracker[job_id] = JobStatus(
            job_id=job_id,
            site_id=site_id,
            status="pending",
            progress=0.0,
            pages_processed=0,
            pages_total=None,
            current_task="Initializing scraping job",
            error_message=None,
            started_at=get_current_timestamp(),
            completed_at=None
        )
        
        # Start background task
        background_tasks.add_task(
            scrape_site_background,
            job_id=job_id,
            site_id=site_id,
            base_url=base_url,
            site_name=request.site_name,
            description=request.description
        )
        
        logger.info(f"Started scraping job {job_id} for site {base_url}")
        
        return ScrapeResponse(
            job_id=job_id,
            site_id=site_id,
            message=f"Scraping job started for {request.site_name}"
        )
        
    except Exception as e:
        logger.error(f"Failed to start scraping: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=ScrapeStatusResponse)
async def get_scraping_status(job_id: str):
    """Get the status of a scraping job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        ScrapeStatusResponse with current status
    """
    if job_id not in job_tracker:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = job_tracker[job_id]
    
    return ScrapeStatusResponse(
        job_id=job_status.job_id,
        status=job_status.status,
        progress=job_status.progress,
        pages_processed=job_status.pages_processed,
        pages_total=job_status.pages_total,
        current_task=job_status.current_task,
        error_message=job_status.error_message,
        started_at=job_status.started_at,
        completed_at=job_status.completed_at
    )

@router.get("/jobs")
async def list_jobs():
    """List all scraping jobs.
    
    Returns:
        List of job statuses
    """
    return {
        "total_jobs": len(job_tracker),
        "jobs": [
            {
                "job_id": job.job_id,
                "status": job.status,
                "progress": job.progress,
                "started_at": job.started_at,
                "completed_at": job.completed_at
            }
            for job in job_tracker.values()
        ]
    }

@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a scraping job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Cancellation confirmation
    """
    if job_id not in job_tracker:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_tracker[job_id]
    
    if job.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed job")
    
    job.status = "cancelled"
    job.error_message = "Job cancelled by user"
    job.completed_at = get_current_timestamp()
    
    return {"message": f"Job {job_id} cancelled successfully"}

@router.get("/sites")
async def list_sites(db: Session = Depends(get_db)):
    """List all scraped sites.
    
    Args:
        db: Database session
        
    Returns:
        List of sites with basic information
    """
    try:
        sites_query = text("""
            SELECT s.id, s.name, s.base_url, s.description, s.created_at,
                   COUNT(sp.id) as page_count,
                   COUNT(pc.id) as chunk_count
            FROM sites s
            LEFT JOIN site_pages sp ON s.id = sp.site_id
            LEFT JOIN page_chunks pc ON sp.id = pc.page_id
            GROUP BY s.id, s.name, s.base_url, s.description, s.created_at
            ORDER BY s.created_at DESC
        """)
        
        result = db.execute(sites_query)
        sites = result.fetchall()
        
        return {
            "total_sites": len(sites),
            "sites": [
                {
                    "id": str(site[0]),
                    "name": site[1],
                    "base_url": site[2],
                    "description": site[3],
                    "created_at": site[4],
                    "page_count": site[5] or 0,
                    "chunk_count": site[6] or 0
                }
                for site in sites
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))