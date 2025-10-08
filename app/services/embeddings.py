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
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult object
            
        Raises:
            RuntimeError: If model is not initialized
        """
        if not hasattr(self, 'model') or self.model is None:
            await self.initialize()
        
        if not text.strip():
            # Return zero vector for empty text
            return EmbeddingResult(
                text=text,
                embedding=[0.0] * self.dimension,
                model_name=self.model_name,
                dimension=self.dimension
            )
        
        try:
            # Generate embedding using LM Studio API
            session = await self.get_session()
            payload = {
                "model": self.model_name,
                "input": text
            }
            
            async with session.post(self.embedding_endpoint, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    embedding_vector = result["data"][0]["embedding"]
                    
                    return EmbeddingResult(
                        text=text,
                        embedding=embedding_vector,
                        model_name=self.model_name,
                        dimension=len(embedding_vector)
                    )
                else:
                    logger.error(f"LM Studio API error: {response.status}")
                    raise Exception(f"Embedding generation failed: {response.status}")
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            # Return zero vector as fallback
            return EmbeddingResult(
                text=text,
                embedding=[0.0] * self.dimension,
                model_name=self.model_name,
                dimension=self.dimension
            )
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of EmbeddingResult objects
        """
        if not hasattr(self, 'model') or self.model is None:
            await self.initialize()
        
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            # Use LM Studio batch API
            session = await self.get_session()
            payload = {
                "model": self.model_name,
                "input": texts
            }
            
            async with session.post(self.embedding_endpoint, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    embedding_data = result["data"]
                    
                    results = []
                    for i, item in enumerate(embedding_data):
                        results.append(EmbeddingResult(
                            text=texts[i],
                            embedding=item["embedding"],
                            model_name=self.model_name,
                            dimension=len(item["embedding"])
                        ))
                    
                    logger.info(f"Successfully generated {len(results)} embeddings")
                    return results
                else:
                    logger.error(f"LM Studio batch API error: {response.status}")
                    raise Exception(f"Batch embedding generation failed: {response.status}")
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            # Return zero vectors as fallback
            return [
                EmbeddingResult(
                    text=text,
                    embedding=[0.0] * self.dimension,
                    model_name=self.model_name,
                    dimension=self.dimension
                )
                for text in texts
            ]
    
    async def embed_chunks(self, chunks: List[ContentChunk]) -> List[Tuple[ContentChunk, EmbeddingResult]]:
        """Generate embeddings for content chunks.
        
        Args:
            chunks: List of ContentChunk objects
            
        Returns:
            List of tuples (chunk, embedding_result)
        """
        if not chunks:
            return []
        
        logger.info(f"Embedding {len(chunks)} chunks")
        
        # Prepare texts for embedding
        texts = []
        for chunk in chunks:
            # Combine title and content for better embeddings
            chunk_text = ""
            if chunk.title:
                chunk_text += f"Title: {chunk.title}\n"
            chunk_text += chunk.content
            texts.append(chunk_text)
        
        # Generate embeddings
        embedding_results = await self.generate_embeddings_batch(texts)
        
        # Pair chunks with their embeddings
        chunk_embeddings = list(zip(chunks, embedding_results))
        
        return chunk_embeddings
    
    async def search_similar_chunks(
        self, 
        query_text: str, 
        chunk_embeddings: List[Tuple[int, List[float]]], 
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """Search for chunks similar to query text.
        
        Args:
            query_text: Query text to search for
            chunk_embeddings: List of tuples (chunk_id, embedding)
            top_k: Number of top results to return
            
        Returns:
            List of tuples (chunk_id, similarity_score) sorted by similarity
        """
        if not query_text.strip() or not chunk_embeddings:
            return []
        
        # Generate query embedding
        query_embedding_result = await self.generate_embedding(query_text)
        query_embedding = query_embedding_result.embedding
        
        # Calculate similarities
        similarities = []
        for chunk_id, chunk_embedding in chunk_embeddings:
            try:
                similarity = calculate_similarity(query_embedding, chunk_embedding)
                similarities.append((chunk_id, similarity))
            except Exception as e:
                logger.warning(f"Failed to calculate similarity for chunk {chunk_id}: {e}")
                similarities.append((chunk_id, 0.0))
        
        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate that an embedding has the correct dimension and format.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(embedding, list):
            return False
        
        if len(embedding) != self.dimension:
            return False
        
        # Check that all values are numbers
        try:
            for value in embedding:
                float(value)
            return True
        except (TypeError, ValueError):
            return False
    
    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize an embedding vector to unit length.
        
        Args:
            embedding: Embedding vector to normalize
            
        Returns:
            Normalized embedding vector
        """
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        
        if norm == 0:
            return embedding  # Return as-is if zero vector
        
        normalized = embedding_array / norm
        return normalized.tolist()
    
    async def get_embedding_stats(self, embeddings: List[List[float]]) -> Dict[str, float]:
        """Get statistics about a collection of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Statistics dictionary
        """
        if not embeddings:
            return {
                'count': 0,
                'dimension': self.dimension,
                'avg_magnitude': 0.0,
                'min_magnitude': 0.0,
                'max_magnitude': 0.0
            }
        
        embeddings_array = np.array(embeddings)
        
        # Calculate magnitudes
        magnitudes = np.linalg.norm(embeddings_array, axis=1)
        
        return{
            'count': len(embeddings),
            'dimension': embeddings_array.shape[1],
            'avg_magnitude': float(np.mean(magnitudes)),
            'min_magnitude': float(np.min(magnitudes)),
            'max_magnitude': float(np.max(magnitudes)),
            'avg_values': {
                'mean': float(np.mean(embeddings_array)),
                'std': float(np.std(embeddings_array)),
                'min': float(np.min(embeddings_array)),
                'max': float(np.max(embeddings_array))
            }
                }

# Global embedding service instance
embedding_service = EmbeddingService()