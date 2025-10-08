"""Tests for RAG query functionality."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from app.services.embeddings import EmbeddingService, EmbeddingResult
from app.services.llm import LLMService, ChunkContext, LLMResponse
from app.services.chunker import ContentChunker, ContentChunk
from app.utils.helpers import calculate_similarity

class TestEmbeddingService:
    """Test cases for EmbeddingService."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create an EmbeddingService instance for testing."""
        return EmbeddingService()
    
    @pytest.mark.asyncio
    async def test_embedding_generation(self, embedding_service):
        """Test single embedding generation."""
        # Mock the SentenceTransformer model
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3] * 256])  # 768-dim vector
        
        embedding_service.model = mock_model
        embedding_service.dimension = 768
        
        result = await embedding_service.generate_embedding("test text")
        
        assert isinstance(result, EmbeddingResult)
        assert result.text == "test text"
        assert len(result.embedding) == 768
        assert result.model_name == embedding_service.model_name
        assert result.dimension == 768
    
    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self, embedding_service):
        """Test batch embedding generation."""
        mock_model = Mock()
        # Return 2 embeddings for 2 texts
        mock_model.encode.return_value = np.array([
            [0.1] * 768,
            [0.2] * 768
        ])
        
        embedding_service.model = mock_model
        embedding_service.dimension = 768
        
        texts = ["text 1", "text 2"]
        results = await embedding_service.generate_embeddings_batch(texts)
        
        assert len(results) == 2
        assert results[0].text == "text 1"
        assert results[1].text == "text 2"
        assert len(results[0].embedding) == 768
        assert len(results[1].embedding) == 768
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, embedding_service):
        """Test handling of empty text inputs."""
        embedding_service.dimension = 768
        
        result = await embedding_service.generate_embedding("")
        
        assert result.text == ""
        assert result.embedding == [0.0] * 768
    
    def test_embedding_validation(self, embedding_service):
        """Test embedding vector validation."""
        embedding_service.dimension = 768
        
        # Valid embedding
        valid_embedding = [0.1] * 768
        assert embedding_service.validate_embedding(valid_embedding) == True
        
        # Wrong dimension
        wrong_dim = [0.1] * 512
        assert embedding_service.validate_embedding(wrong_dim) == False
        
        # Invalid values
        invalid_values = ["not", "numbers"] + [0.1] * 766
        assert embedding_service.validate_embedding(invalid_values) == False
    
    def test_embedding_normalization(self, embedding_service):
        """Test embedding vector normalization."""
        embedding = [3.0, 4.0, 0.0]  # Magnitude = 5
        normalized = embedding_service.normalize_embedding(embedding)
        
        # Check that magnitude is 1
        magnitude = sum(x**2 for x in normalized) ** 0.5
        assert abs(magnitude - 1.0) < 1e-6
    
    @pytest.mark.asyncio
    async def test_similarity_search(self, embedding_service):
        """Test similarity search functionality."""
        # Mock embedding generation
        query_embedding = [1.0, 0.0, 0.0]
        
        with patch.object(embedding_service, 'generate_embedding') as mock_gen:
            mock_gen.return_value = EmbeddingResult(
                text="query",
                embedding=query_embedding,
                model_name="test",
                dimension=3
            )
            
            # Test chunk embeddings (similar to different degrees)
            chunk_embeddings = [
                (1, [1.0, 0.0, 0.0]),  # Identical (similarity = 1.0)
                (2, [0.0, 1.0, 0.0]),  # Orthogonal (similarity = 0.0)
                (3, [0.7, 0.7, 0.0]),  # Partially similar
            ]
            
            results = await embedding_service.search_similar_chunks(
                "query text", chunk_embeddings, top_k=2
            )
            
            assert len(results) == 2
            # Should return most similar chunks first
            assert results[0][0] == 1  # Most similar chunk
            assert results[0][1] > results[1][1]  # Similarity scores in descending order

class TestLLMService:
    """Test cases for LLMService."""
    
    @pytest.fixture
    def llm_service(self):
        """Create an LLMService instance for testing."""
        return LLMService()
    
    @pytest.mark.asyncio
    async def test_connection_test(self, llm_service):
        """Test LM Studio connection."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": [{"id": "phi-3-mini"}]})
        
        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        llm_service.session = mock_session
        
        result = await llm_service._test_connection_impl()
        assert result == True
    
    @pytest.mark.asyncio
    async def test_llm_response_generation(self, llm_service):
        """Test LLM response generation."""
        # Mock LM Studio response
        mock_response_data = {
            "choices": [{
                "message": {"content": "This is a test response."},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 25}
        }
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        
        mock_session = Mock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        llm_service.session = mock_session
        
        response = await llm_service.generate_response("Test prompt")
        
        assert isinstance(response, LLMResponse)
        assert response.content == "This is a test response."
        assert response.tokens_used == 25
        assert response.finish_reason == "stop"
    
    def test_rag_prompt_creation(self, llm_service):
        """Test RAG prompt formatting."""
        contexts = [
            ChunkContext(
                chunk_id=1,
                content="This is test content.",
                title="Test Title",
                url="https://example.com/test",
                similarity_score=0.9
            )
        ]
        
        prompt = llm_service.create_rag_prompt("What is this about?", contexts)
        
        assert "What is this about?" in prompt
        assert "Test Title" in prompt
        assert "This is test content." in prompt
        assert "https://example.com/test" in prompt
        assert "0.900" in prompt  # Similarity score
    
    def test_empty_context_prompt(self, llm_service):
        """Test prompt creation with no context."""
        prompt = llm_service.create_rag_prompt("What is this about?", [])
        
        assert "What is this about?" in prompt
        assert "don't have any specific context" in prompt

class TestContentChunker:
    """Test cases for ContentChunker."""
    
    @pytest.fixture
    def chunker(self):
        """Create a ContentChunker instance for testing."""
        return ContentChunker()
    
    def test_sentence_splitting(self, chunker):
        """Test text splitting into sentences."""
        text = "This is sentence one. This is sentence two! This is sentence three?"
        sentences = chunker._split_into_sentences(text)
        
        assert len(sentences) == 3
        assert "This is sentence one" in sentences[0]
        assert "This is sentence two" in sentences[1]
        assert "This is sentence three" in sentences[2]
    
    def test_content_chunking(self, chunker):
        """Test content chunking with overlap."""
        # Create content that will require multiple chunks
        long_content = " ".join([f"Sentence {i}." for i in range(100)])
        
        chunks = chunker.chunk_content(long_content, title="Test Content")
        
        assert len(chunks) > 1  # Should create multiple chunks
        
        # Check chunk properties
        for chunk in chunks:
            assert isinstance(chunk, ContentChunk)
            assert chunk.token_count > 0
            assert len(chunk.content) > 0
            assert chunk.chunk_number > 0
    
    def test_chunk_overlap(self, chunker):
        """Test that chunks have proper overlap."""
        content = " ".join([f"Unique sentence {i}." for i in range(50)])
        
        chunks = chunker.chunk_content(content)
        
        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            # This is a simplified test - real overlap detection would be more complex
            first_chunk_end = chunks[0].content.split()[-5:]  # Last 5 words
            second_chunk_start = chunks[1].content.split()[:10]  # First 10 words
            
            # Should have some common words due to overlap
            common_words = set(first_chunk_end) & set(second_chunk_start)
            assert len(common_words) > 0
    
    def test_chunk_metadata(self, chunker):
        """Test chunk metadata generation."""
        headers = [
            {"level": 1, "text": "Main Header"},
            {"level": 2, "text": "Sub Header"}
        ]
        
        chunks = chunker.chunk_content(
            "Test content for chunking.",
            title="Test Page",
            headers=headers,
            metadata={"source": "test"}
        )
        
        assert len(chunks) > 0
        chunk = chunks[0]
        
        assert chunk.title is not None
        assert chunk.metadata["source"] == "test"
        assert chunk.metadata["headers"] == headers
        assert "word_count" in chunk.metadata
        assert "character_count" in chunk.metadata

class TestSimilarityCalculation:
    """Test similarity calculation utilities."""
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        # Identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = calculate_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-6
        
        # Orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = calculate_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 1e-6
        
        # Opposite vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = calculate_similarity(vec1, vec2)
        assert similarity == 0.0  # Clamped to 0
    
    def test_similarity_edge_cases(self):
        """Test similarity calculation edge cases."""
        # Zero vectors
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = calculate_similarity(vec1, vec2)
        assert similarity == 0.0
        
        # Different lengths should raise error
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        
        with pytest.raises(ValueError):
            calculate_similarity(vec1, vec2)

if __name__ == "__main__":
    pytest.main([__file__])