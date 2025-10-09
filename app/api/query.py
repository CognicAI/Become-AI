"""API endpoints for RAG query operations."""
import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging
from datetime import datetime

from ..db.db import get_db
from ..models import QueryRequest, QueryResponse, ChunkMetadata
from ..services.embeddings import embedding_service
from ..services.llm import llm_service, ChunkContext
from ..utils.helpers import normalize_url, get_current_timestamp
from ..utils.config import settings

logger = logging.getLogger(__name__)

# Router for query endpoints
router = APIRouter(prefix="/query", tags=["query"])

@router.post("/", response_model=QueryResponse)
async def query_rag_system(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Query the RAG system for answers.
    
    Args:
        request: Query request with question and site URL
        db: Database session
        
    Returns:
        QueryResponse with answer and source chunks
    """
    start_time = get_current_timestamp()
    
    try:
        # Normalize the site URL
        base_url = normalize_url(str(request.site_base_url))
        
        # Check if site exists
        site_query = text("SELECT id FROM sites WHERE base_url = :url")
        site_result = db.execute(site_query, {'url': base_url}).fetchone()
        
        if not site_result:
            raise HTTPException(
                status_code=404,
                detail=f"Site {base_url} not found. Please scrape the site first."
            )
        
        site_id = site_result[0]
        
        # Initialize embedding service
        await embedding_service.initialize()
        
        # Generate query embedding
        query_embedding_result = await embedding_service.generate_embedding(request.question)
        query_embedding = query_embedding_result.embedding
        
        # Search for similar chunks using vector similarity
        similarity_query = text("""
            SELECT 
                pc.id,
                pc.title,
                pc.content,
                pc.chunk_number,
                pc.embedding,
                sp.url,
                sp.title as page_title,
                (pc.embedding <=> :query_embedding::vector) as distance
            FROM page_chunks pc
            JOIN site_pages sp ON pc.page_id = sp.id
            WHERE sp.site_id = :site_id
            ORDER BY pc.embedding <=> :query_embedding::vector
            LIMIT :max_chunks
        """)
        
        chunks_result = db.execute(similarity_query, {
            'query_embedding': query_embedding,
            'site_id': site_id,
            'max_chunks': request.max_chunks
        })
        
        chunks = chunks_result.fetchall()
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"No content found for site {base_url}. The site may not have been processed yet."
            )
        
        # Convert to ChunkContext objects
        chunk_contexts = []
        chunk_metadata = []
        
        for chunk in chunks:
            # Convert distance to similarity score (0-1, higher is better)
            # PostgreSQL distance is 1 - cosine_similarity, so similarity = 1 - distance
            similarity_score = max(0.0, 1.0 - chunk[7])
            
            chunk_context = ChunkContext(
                chunk_id=chunk[0],
                content=chunk[2],
                title=chunk[1],
                url=chunk[5],
                similarity_score=similarity_score
            )
            chunk_contexts.append(chunk_context)
            
            chunk_metadata.append(ChunkMetadata(
                chunk_id=chunk[0],
                chunk_number=chunk[3],
                page_url=chunk[5],
                page_title=chunk[6],
                similarity_score=similarity_score
            ))
        
        # Generate answer using LLM
        async with llm_service as llm:
            llm_response = await llm.answer_question(request.question, chunk_contexts)
        
        processing_time = (get_current_timestamp() - start_time).total_seconds()
        
        logger.info(f"Query processed in {processing_time:.2f}s: '{request.question[:50]}...'")
        
        return QueryResponse(
            answer=llm_response.content,
            chunks_used=chunk_metadata,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream")
async def query_rag_system_stream(
    question: str,
    site_base_url: str,
    max_chunks: int = 5,
    db: Session = Depends(get_db)
):
    """Stream RAG system responses using Server-Sent Events.
    
    Args:
        question: Question to ask
        site_base_url: Base URL of the site to query
        max_chunks: Maximum number of chunks to retrieve
        db: Database session
        
    Returns:
        StreamingResponse with SSE events
    """
    async def generate_stream():
        try:
            # Normalize the site URL
            base_url = normalize_url(site_base_url)
            
            # Check if site exists
            site_query = text("SELECT id FROM sites WHERE base_url = :url")
            site_result = db.execute(site_query, {'url': base_url}).fetchone()
            
            if not site_result:
                yield f"data: {json.dumps({'error': f'Site {base_url} not found'})}\n\n"
                return
            
            site_id = site_result[0]
            
            # Initialize embedding service
            await embedding_service.initialize()
            
            # Send status update
            yield f"data: {json.dumps({'status': 'Searching for relevant content...'})}\n\n"
            
            # Generate query embedding
            query_embedding_result = await embedding_service.generate_embedding(question)
            query_embedding = query_embedding_result.embedding
            
            # Search for similar chunks
            similarity_query = text("""
                SELECT 
                    pc.id,
                    pc.title,
                    pc.content,
                    pc.chunk_number,
                    pc.embedding,
                    sp.url,
                    sp.title as page_title,
                    (pc.embedding <=> :query_embedding::vector) as distance
                FROM page_chunks pc
                JOIN site_pages sp ON pc.page_id = sp.id
                WHERE sp.site_id = :site_id
                ORDER BY pc.embedding <=> :query_embedding::vector
                LIMIT :max_chunks
            """)
            
            chunks_result = db.execute(similarity_query, {
                'query_embedding': query_embedding,
                'site_id': site_id,
                'max_chunks': max_chunks
            })
            
            chunks = chunks_result.fetchall()
            
            if not chunks:
                yield f"data: {json.dumps({'error': 'No relevant content found'})}\n\n"
                return
            
            # Send chunk metadata
            chunk_metadata = []
            chunk_contexts = []
            
            for chunk in chunks:
                similarity_score = max(0.0, 1.0 - chunk[7])
                
                chunk_context = ChunkContext(
                    chunk_id=chunk[0],
                    content=chunk[2],
                    title=chunk[1],
                    url=chunk[5],
                    similarity_score=similarity_score
                )
                chunk_contexts.append(chunk_context)
                
                chunk_metadata.append({
                    'chunk_id': chunk[0],
                    'chunk_number': chunk[3],
                    'page_url': chunk[5],
                    'page_title': chunk[6],
                    'similarity_score': similarity_score
                })
            
            yield f"data: {json.dumps({'chunks': chunk_metadata})}\n\n"
            yield f"data: {json.dumps({'status': 'Generating answer...'})}\n\n"
            
            # Stream the answer
            async with llm_service as llm:
                async for token in llm.answer_question_stream(question, chunk_contexts):
                    yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Streaming query failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.get("/similar-chunks")
async def find_similar_chunks(
    input_text: str,
    site_base_url: str,
    max_chunks: int = 10,
    db: Session = Depends(get_db)
):
    """Find chunks similar to given text.
    
    Args:
        text: Text to find similar chunks for
        site_base_url: Base URL of the site to search
        max_chunks: Maximum number of chunks to return
        db: Database session
        
    Returns:
        List of similar chunks with metadata
    """
    try:
        # Normalize the site URL
        base_url = normalize_url(site_base_url)
        
        # Check if site exists
        site_query = text("SELECT id FROM sites WHERE base_url = :url")
        site_result = db.execute(site_query, {'url': base_url}).fetchone()
        
        if not site_result:
            raise HTTPException(
                status_code=404,
                detail=f"Site {base_url} not found"
            )
        
        site_id = site_result[0]
        
        # Initialize embedding service
        await embedding_service.initialize()
        
        # Generate text embedding
        text_embedding_result = await embedding_service.generate_embedding(input_text)
        text_embedding = text_embedding_result.embedding
        
        # Search for similar chunks
        similarity_query = text("""
                    SELECT 
                    pc.id,
                    pc.title,
                    pc.summary,
                    pc.content,
                    pc.chunk_number,
                    pc.token_count,
                    sp.url,
                    sp.title as page_title,
                    (pc.embedding <=> :text_embedding::vector) as distance
                    FROM page_chunks pc
                    JOIN site_pages sp ON pc.page_id = sp.id
                    WHERE sp.site_id = :site_id
                    ORDER BY pc.embedding <=> :text_embedding::vector
                    LIMIT :max_chunks
        """)
        
        chunks_result = db.execute(similarity_query, {
            'text_embedding': text_embedding,
            'site_id': site_id,
            'max_chunks': max_chunks
        })
        
        chunks = chunks_result.fetchall()
        
        similar_chunks = []
        for chunk in chunks:
            similarity_score = max(0.0, 1.0 - chunk[8])
            
            similar_chunks.append({
                'chunk_id': chunk[0],
                'title': chunk[1],
                'summary': chunk[2],
                'content': chunk[3][:500] + '...' if len(chunk[3]) > 500 else chunk[3],
                'chunk_number': chunk[4],
                'token_count': chunk[5],
                'page_url': chunk[6],
                'page_title': chunk[7],
                'similarity_score': similarity_score
            })
        
        return {
            'query_text': input_text,
            'site_url': base_url,
            'total_chunks': len(similar_chunks),
            'chunks': similar_chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar chunks search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chunk/{chunk_id}")
async def get_chunk_details(
    chunk_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific chunk.
    
    Args:
        chunk_id: Chunk identifier
        db: Database session
        
    Returns:
        Detailed chunk information
    """
    try:
        chunk_query = text("""
            SELECT 
                pc.id,
                pc.title,
                pc.summary,
                pc.content,
                pc.chunk_number,
                pc.token_count,
                pc.metadata,
                pc.created_at,
                sp.url,
                sp.title as page_title,
                s.name as site_name,
                s.base_url as site_url
            FROM page_chunks pc
            JOIN site_pages sp ON pc.page_id = sp.id
            JOIN sites s ON sp.site_id = s.id
            WHERE pc.id = :chunk_id
        """)
        
        chunk_result = db.execute(chunk_query, {'chunk_id': chunk_id}).fetchone()
        
        if not chunk_result:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return {
            'chunk_id': chunk_result[0],
            'title': chunk_result[1],
            'summary': chunk_result[2],
            'content': chunk_result[3],
            'chunk_number': chunk_result[4],
            'token_count': chunk_result[5],
            'metadata': chunk_result[6],
            'created_at': chunk_result[7],
            'page_url': chunk_result[8],
            'page_title': chunk_result[9],
            'site_name': chunk_result[10],
            'site_url': chunk_result[11]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chunk details failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))