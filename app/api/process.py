"""API endpoints for processing content metadata."""
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from ..db.db import get_db, SessionLocal
from ..services.llm import llm_service
from ..utils.helpers import get_current_timestamp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["process"])

async def process_single_chunk(row: Any, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """Process a single chunk with concurrency control."""
    chunk_id, content, url, old_title, old_summary = row
    
    async with semaphore:
        logger.info(f"Processing chunk {chunk_id} (Page URL: {url})")
        db = SessionLocal()
        try:
            # Generate title
            new_title = await llm_service.generate_chunk_title(content)
            
            # Generate summary
            new_summary = await llm_service.generate_chunk_summary(content, title=new_title)
            
            # Update database
            update_query = text("""
                UPDATE page_chunks 
                SET title = :title, 
                    summary = :summary,
                    is_metadata_updated = TRUE
                WHERE id = :chunk_id
            """)
            db.execute(update_query, {
                'title': new_title,
                'summary': new_summary,
                'chunk_id': chunk_id
            })
            db.commit()
            logger.debug(f"Updated metadata for chunk {chunk_id}")
            
            return {
                "chunk_id": chunk_id,
                "before": {
                    "title": old_title,
                    "summary": old_summary
                },
                "after": {
                    "title": new_title,
                    "summary": new_summary
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_id}: {e}")
            return {
                "chunk_id": chunk_id,
                "error": str(e)
            }
        finally:
            db.close()

async def process_page_hierarchy(page_row: Any, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """Process a page and its chunks hierarchically."""
    page_id, page_url, old_page_title, old_page_summary = page_row
    
    logger.info(f"Processing page hierarchy for {page_url} (ID: {page_id})")
    
    db = SessionLocal()
    try:
        # Fetch chunks for this page that haven't been updated yet
        chunks_query = text("""
            SELECT id, content, :url, title, summary 
            FROM page_chunks 
            WHERE page_id = :page_id
            AND is_metadata_updated = FALSE
            ORDER BY chunk_number
        """)
        chunk_rows = db.execute(chunks_query, {'page_id': page_id, 'url': page_url}).fetchall()
        
        if not chunk_rows:
            logger.warning(f"No chunks found for page {page_id}")
            return {"page_id": page_id, "error": "No chunks found"}
            
        # Process chunks concurrently
        chunk_tasks = [process_single_chunk(row, semaphore) for row in chunk_rows]
        chunk_results = await asyncio.gather(*chunk_tasks)
        
        # Aggregate summaries
        valid_summaries = []
        for r in chunk_results:
            if 'after' in r and 'summary' in r['after']:
                valid_summaries.append(r['after']['summary'])
        
        aggregated_text = "\n".join(valid_summaries)
        
        if not aggregated_text:
            logger.warning(f"No valid summaries generated for page {page_id}")
            return {"page_id": page_id, "error": "Failed to generate chunk summaries"}
            
        # Generate page title and summary from aggregated text
        logger.info(f"Generating page-level metadata for {page_url}")
        
        # Use LLM to summarize the aggregated summaries
        # We treat the aggregated summaries as the "content" for the page level
        page_title = await llm_service.generate_chunk_title(aggregated_text)
        page_summary = await llm_service.generate_chunk_summary(aggregated_text, title=page_title)
        
        # Update site_pages
        update_page_query = text("""
            UPDATE site_pages 
            SET title = :title, 
                summary = :summary,
                is_metadata_updated = TRUE
            WHERE id = :page_id
        """)
        db.execute(update_page_query, {
            'title': page_title,
            'summary': page_summary,
            'page_id': page_id
        })
        db.commit()
        
        return {
            "page_id": page_id,
            "url": page_url,
            "before": {
                "title": old_page_title,
                "summary": old_page_summary
            },
            "after": {
                "title": page_title,
                "summary": page_summary
            },
            "chunks": chunk_results
        }
        
    except Exception as e:
        logger.error(f"Error processing page {page_id}: {e}")
        return {"page_id": page_id, "error": str(e)}
    finally:
        db.close()

async def generate_metadata_logic(site_id: Optional[int] = None, limit: Optional[int] = None):
    """Core logic to generate hierarchical metadata."""
    logger.info(f"Starting hierarchical metadata generation. Site ID: {site_id if site_id else 'All'}, Limit: {limit if limit else 'None'}")
    
    db = SessionLocal()
    try:
        # Fetch pages to process (only those with at least one unprocessed chunk)
        # Build the subquery to find page IDs with unprocessed chunks
        subquery = """
            SELECT DISTINCT sp.id
            FROM site_pages sp
            INNER JOIN page_chunks pc ON sp.id = pc.page_id
            WHERE pc.is_metadata_updated = FALSE
        """
        params = {}
        
        if site_id:
            subquery += " AND sp.site_id = :site_id"
            params['site_id'] = site_id
        
        # Now select full page details only for those IDs
        query_str = f"""
            SELECT id, url, title, summary 
            FROM site_pages
            WHERE id IN ({subquery})
        """
            
        if limit:
            query_str += " LIMIT :limit"
            params['limit'] = limit
            
        page_rows = db.execute(text(query_str), params).fetchall()
        
        total_pages = len(page_rows)
        logger.info(f"Found {total_pages} pages to process")
        
        # Concurrency control
        semaphore = asyncio.Semaphore(5)
        
        # Initialize LLM service
        async with llm_service:
            # Process pages (which internally process chunks)
            # We can process pages concurrently too, but let's be careful not to spawn too many tasks
            # Since process_page_hierarchy spawns tasks for chunks, maybe we should process pages sequentially 
            # or with a limited concurrency. The semaphore is passed down, so it limits TOTAL concurrent LLM calls.
            # So it's safe to gather all page tasks.
            
            tasks = [process_page_hierarchy(row, semaphore) for row in page_rows]
            results = await asyncio.gather(*tasks)
            
        logger.info("Metadata generation completed")
        return results
        
    except Exception as e:
        logger.error(f"Metadata generation failed: {e}")
        raise
    finally:
        db.close()

async def process_metadata_generation(site_id: Optional[int] = None):
    """Background task wrapper."""
    await generate_metadata_logic(site_id=site_id)

@router.post("/generate-metadata")
async def generate_metadata(
    background_tasks: BackgroundTasks,
    site_id: Optional[int] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Trigger hierarchical generation of titles and summaries.
    
    - **site_id**: Optional ID of the site to process.
    - **limit**: Optional number of **pages** to process. 
      - If provided, runs synchronously and returns results.
      - If NOT provided, runs in background.
    """
    # Verify site_id if provided
    if site_id:
        site = db.execute(text("SELECT id FROM sites WHERE id = :id"), {'id': site_id}).fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
    
    if limit:
        # Run synchronously and return results
        results = await generate_metadata_logic(site_id=site_id, limit=limit)
        return {
            "message": f"Processed {len(results)} pages",
            "results": results
        }
    else:
        # Run in background
        background_tasks.add_task(process_metadata_generation, site_id)
        return {
            "message": "Metadata generation started in background",
            "site_id": site_id
        }
