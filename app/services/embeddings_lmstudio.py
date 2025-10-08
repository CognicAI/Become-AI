"""Embedding generation and vector storage service using LM Studio."""
import asyncio
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass
import aiohttp
import json

from ..utils.config import settings
from ..utils.helpers import calculate_similarity
from ..services.chunker import ContentChunk

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Container for embedding generation result."""
    text: str
    embedding: List[float]
    model_name: str
    dimension: int

class EmbeddingService:
    """Service for generating and managing embeddings using LM Studio."""
    
    def __init__(self):
        """Initialize the embedding service."""
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.lm_studio_url = settings.lmstudio_url
        self.embedding_endpoint = f"{self.lm_studio_url}/v1/embeddings"
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=60)
                self._session = aiohttp.ClientSession(timeout=timeout)
            return self._session
    
    async def initialize(self):
        """Initialize the embedding service and test LM Studio connection."""
        logger.info(f"Initializing LM Studio embedding service: {self.lm_studio_url}")
        
        try:
            # Test connection to LM Studio
            session = await self.get_session()
            async with session.get(f"{self.lm_studio_url}/v1/models") as response:
                if response.status == 200:
                    models = await response.json()
                    logger.info("✅ LM Studio connection successful")
                    
                    # Log available models
                    if models.get("data"):
                        model_names = [model.get("id", "Unknown") for model in models["data"]]
                        logger.info(f"Available models: {model_names}")
                    
                    # Check if our embedding model is available
                    embedding_models = [m for m in models.get("data", []) 
                                      if "embed" in m.get("id", "").lower() or 
                                         "bge" in m.get("id", "").lower()]
                    
                    if embedding_models:
                        logger.info(f"Embedding models found: {[m['id'] for m in embedding_models]}")
                    else:
                        logger.warning("⚠️  No embedding models detected in LM Studio")
                        logger.warning("💡 Load an embedding model (like BAAI/bge-base-en-v1.5) in LM Studio")
                else:
                    logger.error(f"❌ LM Studio connection failed: {response.status}")
                    raise Exception(f"LM Studio not accessible at {self.lm_studio_url}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to initialize LM Studio embedding service: {e}")
            logger.error("💡 Make sure LM Studio is running with an embedding model loaded")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using LM Studio."""
        if not text.strip():
            return [0.0] * self.dimension
        
        try:
            session = await self.get_session()
            
            payload = {
                "input": text,
                "model": self.model_name
            }
            
            async with session.post(
                self.embedding_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    if "data" in result and len(result["data"]) > 0:
                        embedding = result["data"][0]["embedding"]
                        
                        # Validate embedding dimension
                        if len(embedding) != self.dimension:
                            logger.warning(f"Embedding dimension mismatch: got {len(embedding)}, expected {self.dimension}")
                            # Pad or truncate as needed
                            if len(embedding) < self.dimension:
                                embedding.extend([0.0] * (self.dimension - len(embedding)))
                            else:
                                embedding = embedding[:self.dimension]
                        
                        return embedding
                    else:
                        logger.error("No embedding data in LM Studio response")
                        return [0.0] * self.dimension
                        
                else:
                    error_text = await response.text()
                    logger.error(f"LM Studio embedding request failed: {response.status} - {error_text}")
                    return [0.0] * self.dimension
                    
        except Exception as e:
            logger.error(f"Error generating embedding via LM Studio: {e}")
            return [0.0] * self.dimension
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts via LM Studio")
        
        results = []
        
        # Process in smaller batches to avoid timeouts
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Process each text in the batch
            for text in batch:
                embedding = await self.generate_embedding(text)
                
                result = EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model_name=self.model_name,
                    dimension=len(embedding)
                )
                results.append(result)
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
        
        logger.info(f"Generated {len(results)} embeddings successfully")
        return results
    
    async def store_chunk_embeddings(self, chunks: List[ContentChunk], page_id: str) -> List[str]:
        """Generate and store embeddings for content chunks."""
        if not chunks:
            return []
        
        logger.info(f"Processing {len(chunks)} chunks for embeddings")
        
        # Generate embeddings for all chunk contents
        texts = [chunk.content for chunk in chunks]
        embedding_results = await self.generate_embeddings_batch(texts)
        
        chunk_ids = []
        
        # Store each chunk with its embedding
        from ..db.db import get_session, PageChunk
        
        try:
            session = get_session()
            
            for i, (chunk, embedding_result) in enumerate(zip(chunks, embedding_results)):
                
                # Create database record
                db_chunk = PageChunk(
                    page_id=page_id,
                    chunk_number=chunk.chunk_number,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    embedding=embedding_result.embedding,
                    metadata_={
                        "url": chunk.url,
                        "headers": chunk.headers,
                        "chunk_size": len(chunk.content),
                        "model_name": embedding_result.model_name
                    }
                )
                
                session.add(db_chunk)
                session.flush()  # Get the ID
                chunk_ids.append(str(db_chunk.id))
            
            session.commit()
            logger.info(f"Stored {len(chunk_ids)} chunk embeddings successfully")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing chunk embeddings: {e}")
            raise
        finally:
            session.close()
        
        return chunk_ids
    
    async def search_similar_chunks(self, query_text: str, site_base_url: str, 
                                  top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """Search for similar chunks using cosine similarity."""
        logger.info(f"Searching for chunks similar to query (top_k={top_k})")
        
        # Generate embedding for query
        query_embedding = await self.generate_embedding(query_text)
        
        if not query_embedding or all(x == 0.0 for x in query_embedding):
            logger.warning("Failed to generate valid query embedding")
            return []
        
        # Search database for similar chunks
        from ..db.db import get_session, PageChunk, SitePage, Site
        from sqlalchemy.orm import joinedload
        from sqlalchemy import func
        
        try:
            session = get_session()
            
            # Query chunks with their page and site info
            query = session.query(PageChunk).join(SitePage).join(Site).filter(
                Site.base_url == site_base_url
            ).options(
                joinedload(PageChunk.page).joinedload(SitePage.site)
            )
            
            chunks = query.all()
            
            if not chunks:
                logger.info(f"No chunks found for site: {site_base_url}")
                return []
            
            logger.info(f"Calculating similarity for {len(chunks)} chunks")
            
            # Calculate similarities
            similarities = []
            for chunk in chunks:
                if chunk.embedding:
                    similarity = calculate_similarity(query_embedding, chunk.embedding)
                    if similarity >= threshold:
                        similarities.append({
                            "chunk_id": str(chunk.id),
                            "content": chunk.content,
                            "similarity": similarity,
                            "url": chunk.page.url,
                            "title": chunk.page.title or "Untitled",
                            "token_count": chunk.token_count,
                            "metadata": chunk.metadata_
                        })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            results = similarities[:top_k]
            
            logger.info(f"Found {len(results)} similar chunks above threshold {threshold}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
        finally:
            session.close()
    
    async def cleanup(self):
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_embedding_stats(self, embeddings: List[List[float]]) -> Dict[str, float]:
        """Calculate statistics for a set of embeddings."""
        if not embeddings:
            return {}
        
        embeddings_array = np.array(embeddings)
        magnitudes = np.linalg.norm(embeddings_array, axis=1)
        
        return {
            'count': len(embeddings),
            'dimension': embeddings_array.shape[1],
            'avg_magnitude': float(np.mean(magnitudes)),
            'min_magnitude': float(np.min(magnitudes)),
            'max_magnitude': float(np.max(magnitudes)),
            'std_magnitude': float(np.std(magnitudes))
        }