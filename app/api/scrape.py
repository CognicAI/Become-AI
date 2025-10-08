"""API endpoints for web scraping operations."""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import json
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from ..db.db import get_db
from ..models import ScrapeRequest, ScrapeResponse, ScrapeStatusResponse, JobStatus
from ..services.scraper import WebScraper
from ..services.chunker import ContentChunker
from ..services.embeddings import EmbeddingService
from ..utils.helpers import generate_job_id, normalize_url, get_current_timestamp
from ..utils.config import settings

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Job tracking
job_tracker: Dict[str, JobStatus] = {}

# Initialize services
embedding_service = EmbeddingService()

async def process_scraping_job(job_id: str, base_url: str, site_id: str):
    """Background task to process scraping job."""
    try:
        logger.info(f"Starting scraping job {job_id} for site {base_url}")
        
        # Initialize embedding service
        await embedding_service.initialize()
        
        chunker = ContentChunker()
        
        # Start scraping
        job_tracker[job_id].current_task = "Discovering pages"
        
        async with WebScraper() as scraper:
            # Scrape the site
            scraped_pages = await scraper.scrape_site(base_url, max_pages=1000)
            
            if not scraped_pages:
                job_tracker[job_id].status = "failed"
                job_tracker[job_id].error_message = "No pages found to scrape"
                return
            
            job_tracker[job_id].pages_total = len(scraped_pages)
            job_tracker[job_id].current_task = "Processing pages"
            
            # Process pages in database
            from ..db.db import SessionLocal
            db = SessionLocal()
            
            try:
                for i, page in enumerate(scraped_pages):
                    # Insert page into database with JSON-serialized metadata
                    page_query = text("""
                        INSERT INTO site_pages (site_id, url, title, summary, content, metadata, scraped_at)
                        VALUES (:site_id, :url, :title, :summary, :content, :metadata, :scraped_at)
                        RETURNING id
                    """)
                    
                    # Convert metadata dict to JSON string for PostgreSQL JSONB
                    metadata_json = json.dumps(page.metadata) if page.metadata else '{}'
                    
                    page_result = db.execute(page_query, {
                        'site_id': str(site_id),
                        'url': page.url,
                        'title': page.title,
                        'summary': page.summary,
                        'content': page.content,
                        'metadata': metadata_json,  # ✅ Fixed: JSON string instead of dict
                        'scraped_at': get_current_timestamp()
                    })
                    
                    page_row = page_result.fetchone()
                    if page_row:
                        page_id = page_row[0]
                    else:
                        logger.error(f"Failed to insert page: {page.url}")
                        continue
                    
                    # Generate chunks for this page
                    chunks = chunker.chunk_content(
                        content=page.content,
                        title=page.title,
                        headers=page.headers,
                        metadata=page.metadata
                    )
                    
                    if chunks:
                        # Generate embeddings for chunks  
                        chunk_embeddings = await embedding_service.embed_chunks(chunks)
                        logger.info(f"Generated embeddings for {len(chunk_embeddings)} chunks for page: {page.title}")
                    
                    # Update progress
                    job_tracker[job_id].pages_processed = i + 1
                    job_tracker[job_id].progress = (i + 1) / len(scraped_pages) * 100
                    job_tracker[job_id].current_task = f"Processing page {i+1}/{len(scraped_pages)}: {page.title[:50]}..."
                
                db.commit()
                logger.info(f"Successfully processed {len(scraped_pages)} pages")
                
                # Mark job as complete
                job_tracker[job_id].status = "completed" 
                job_tracker[job_id].progress = 100.0
                job_tracker[job_id].current_task = "Completed"
                job_tracker[job_id].completed_at = get_current_timestamp()
                
            except Exception as e:
                db.rollback()
                logger.error(f"Database error processing pages: {e}")
                job_tracker[job_id].status = "failed"
                job_tracker[job_id].error_message = f"Database error: {str(e)}"
            finally:
                db.close()
                
    except Exception as e:
        logger.error(f"Scraping job {job_id} failed: {e}")
        job_tracker[job_id].status = "failed"
        job_tracker[job_id].error_message = str(e)

@router.post("/", response_model=ScrapeResponse)
async def start_scraping(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start a website scraping job."""
    try:
        # Validate and normalize URL
        base_url = normalize_url(str(request.base_url))
        if not base_url:
            raise HTTPException(status_code=400, detail="Invalid base URL")
        
        # Check if site already exists
        existing_site = db.execute(
            text("SELECT id FROM sites WHERE base_url = :base_url"),
            {"base_url": base_url}
        ).fetchone()
        
        if existing_site:
            # Site exists, use existing ID
            site_id = existing_site[0]
            logger.info(f"Using existing site record: {site_id}")
        else:
            # Create new site record
            site_query = text("""
                INSERT INTO sites (id, name, base_url, description, created_at)
                VALUES (gen_random_uuid(), :name, :base_url, :description, :created_at)
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
            logger.info(f"Created new site record: {site_id}")
        
        # Generate job ID
        job_id = generate_job_id(base_url)
        
        # Initialize job tracking
        job_tracker[job_id] = JobStatus(
            job_id=job_id,
            site_id=uuid.UUID(str(site_id)),
            status="running",
            progress=0.0,
            pages_total=0,
            pages_processed=0,
            current_task="Initializing...",
            started_at=get_current_timestamp()
        )
        
        # Start background scraping task
        background_tasks.add_task(process_scraping_job, job_id, base_url, str(site_id))
        
        logger.info(f"Started scraping job {job_id} for site {base_url}")
        
        return ScrapeResponse(
            job_id=job_id,
            message=f"Scraping job started for {base_url}",
            site_id=str(site_id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting scrape job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")

@router.get("/status/{job_id}", response_model=ScrapeStatusResponse)
async def get_scrape_status(job_id: str):
    """Get the status of a scraping job."""
    if job_id not in job_tracker:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = job_tracker[job_id]
    
    return ScrapeStatusResponse(
        job_id=job_id,
        status=job_status.status,
        progress=job_status.progress,
        pages_total=job_status.pages_total,
        pages_processed=job_status.pages_processed,
        current_task=job_status.current_task,
        started_at=job_status.started_at,
        completed_at=job_status.completed_at,
        error_message=job_status.error_message
    )

@router.get("/jobs")
async def list_scrape_jobs():
    """List all scraping jobs."""
    return {
        "jobs": [
            {
                "job_id": job_id,
                "status": job.status,
                "progress": job.progress,
                "started_at": job.started_at,
                "completed_at": job.completed_at
            }
            for job_id, job in job_tracker.items()
        ]
    }