"""LLM integration service for Phi-3 Mini via LM Studio."""
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, AsyncIterator, Any
import logging
from dataclasses import dataclass

from ..utils.config import settings
from ..utils.helpers import get_current_timestamp

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Container for LLM response."""
    content: str
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    processing_time: Optional[float] = None

@dataclass
class ChunkContext:
    """Context chunk for LLM prompts."""
    chunk_id: int
    content: str
    title: Optional[str]
    url: str
    similarity_score: float

class LLMService:
    """Service for interacting with Phi-3 Mini via LM Studio."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.base_url = settings.lmstudio_url.rstrip('/')
        self.model_name = settings.lm_model_name
        self.max_tokens = settings.lm_max_tokens
        self.temperature = settings.lm_temperature
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=120)  # Longer timeout for LLM responses
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_connection(self) -> bool:
        """Test connection to LM Studio.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.session:
            async with self:
                return await self._test_connection_impl()
        else:
            return await self._test_connection_impl()
    
    async def _test_connection_impl(self) -> bool:
        """Internal implementation of connection test."""
        try:
            # Try to get model info
            url = f"{self.base_url}/v1/models"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json() or {}
                    logger.info(f"LM Studio connection successful. Available models: {len(data.get('data', []))}")
                    return True
                else:
                    logger.error(f"LM Studio connection failed with status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to LM Studio: {e}")
            return False
    
    async def generate_response(
        self, 
        prompt: str, 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> LLMResponse:
        """Generate a response from the LLM.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            LLMResponse object
            
        Raises:
            aiohttp.ClientError: If request fails
        """
        if not self.session:
            raise RuntimeError("LLM service not initialized. Use async context manager.")
        
        start_time = get_current_timestamp()
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            "stream": stream
        }
        
        url = f"{self.base_url}/v1/chat/completions"
        
        try:
            async with self.session.post(url, json=payload) as response:
                data = {}
                if response.status != 200:
                    error_text = await response.text()
                    raise aiohttp.ClientError(f"LLM request failed: {response.status} - {error_text}")
                
                if stream:
                    # For streaming, we need to handle differently
                    content = ""
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        if line_text.startswith('data: '):
                            data_str = line_text[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get('choices', [{}])[0].get('delta', {})
                                if 'content' in delta:
                                    content += delta['content']
                            except json.JSONDecodeError:
                                continue
                else:
                    data = await response.json() or {}
                    # Safely extract content
                    choices = data.get('choices', [])
                    if choices and isinstance(choices, list) and 'message' in choices[0]:
                        content = choices[0]['message'].get('content', '')
                    else:
                        content = ''
                
                processing_time = (get_current_timestamp() - start_time).total_seconds()
                # Determine tokens_used and finish_reason for non-streaming responses
                if stream:
                    tokens = None
                    finish = None
                else:
                    tokens = data.get('usage', {}).get('total_tokens')
                    finish = data.get('choices', [{}])[0].get('finish_reason')
                return LLMResponse(
                    content=content,
                    tokens_used=tokens,
                    model=self.model_name,
                    finish_reason=finish,
                    processing_time=processing_time
                )
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    async def generate_response_stream(self, prompt: str, max_tokens: Optional[int] = None) -> AsyncIterator[str]:
        """Generate a streaming response from the LLM.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Yields:
            Response tokens as they are generated
        """
        if not self.session:
            raise RuntimeError("LLM service not initialized. Use async context manager.")
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature,
            "stream": True
        }
        
        url = f"{self.base_url}/v1/chat/completions"
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise aiohttp.ClientError(f"LLM request failed: {response.status} - {error_text}")
                
                async for line in response.content:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get('choices', [{}])[0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            raise
    
    def create_rag_prompt(self, question: str, contexts: List[ChunkContext]) -> str:
        """Create a RAG prompt with retrieved contexts.
        
        Args:
            question: User's question
            contexts: Retrieved context chunks
            
        Returns:
            Formatted prompt string
        """
        if not contexts:
            return f"""Please answer the following question:

Question: {question}

I don't have any specific context to answer this question. Please provide a helpful response based on your general knowledge, but note that you don't have access to specific documents or sources for this query."""
        
        # Format contexts
        context_text = ""
        for i, context in enumerate(contexts, 1):
            context_text += f"\n--- Context {i} ---\n"
            if context.title:
                context_text += f"Title: {context.title}\n"
            context_text += f"Source: {context.url}\n"
            context_text += f"Relevance Score: {context.similarity_score:.3f}\n"
            context_text += f"Content: {context.content}\n"
        
        prompt = f"""You are a helpful AI assistant that answers questions based on provided context. Please follow these guidelines:

1. Answer the question using only the information provided in the context
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Include citations to the sources when referencing specific information
4. Be accurate and concise
5. If multiple contexts provide conflicting information, acknowledge this

Context Information:
{context_text}

Question: {question}

Answer:"""
        
        return prompt
    
    async def generate_chunk_summary(self, content: str, title: Optional[str] = None) -> str:
        """Generate a summary for a content chunk.
        
        Args:
            content: Content to summarize
            title: Optional title for context
            
        Returns:
            Generated summary
        """
        prompt = f"""Please create a concise summary (1-2 sentences) of the following content:

{f'Title: {title}' if title else ''}
Content: {content[:1000]}{'...' if len(content) > 1000 else ''}

Summary:"""
        
        try:
            response = await self.generate_response(prompt, max_tokens=100, temperature=0.3)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate chunk summary: {e}")
            # Fallback: use first sentence
            sentences = content.split('. ')
            if sentences:
                return sentences[0] + ('.' if not sentences[0].endswith('.') else '')
            return "Content summary unavailable."
    
    async def generate_chunk_title(self, content: str) -> str:
        """Generate a title for a content chunk.
        
        Args:
            content: Content to generate title for
            
        Returns:
            Generated title
        """
        prompt = f"""Please create a short, descriptive title (3-8 words) for the following content:

Content: {content[:500]}{'...' if len(content) > 500 else ''}

Title:"""
        
        try:
            response = await self.generate_response(prompt, max_tokens=20, temperature=0.3)
            return response.content.strip().strip('"\'')
        except Exception as e:
            logger.error(f"Failed to generate chunk title: {e}")
            # Fallback: use first few words
            words = content.split()[:5]
            return ' '.join(words) + ('...' if len(words) == 5 else '')
    
    async def answer_question(self, question: str, contexts: List[ChunkContext]) -> LLMResponse:
        """Answer a question using retrieved contexts.
        
        Args:
            question: User's question
            contexts: Retrieved context chunks
            
        Returns:
            LLMResponse with the answer
        """
        prompt = self.create_rag_prompt(question, contexts)
        return await self.generate_response(prompt)
    
    async def answer_question_stream(self, question: str, contexts: List[ChunkContext]) -> AsyncIterator[str]:
        """Answer a question using retrieved contexts with streaming.
        
        Args:
            question: User's question
            contexts: Retrieved context chunks
            
        Yields:
            Response tokens as they are generated
        """
        prompt = self.create_rag_prompt(question, contexts)
        async for token in self.generate_response_stream(prompt):
            yield token

# Global LLM service instance
llm_service = LLMService()