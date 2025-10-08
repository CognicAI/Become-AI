"""Content chunking and tokenization service."""
import re
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass

from ..utils.config import settings
from ..utils.helpers import clean_text

logger = logging.getLogger(__name__)

@dataclass
class ContentChunk:
    """Container for a content chunk."""
    chunk_number: int
    title: Optional[str]
    summary: Optional[str]
    content: str
    token_count: int
    metadata: Dict[str, any]

class TokenCounter:
    """Simple token counter for approximating token counts."""
    
    def count_tokens(self, text: str) -> int:
        """Count approximate tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Approximate token count
        """
        if not text:
            return 0
        
        # Simple approximation: split on whitespace and punctuation
        # This is a rough estimate - real tokenizers are more complex
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Approximate tokens per word (accounting for subword tokenization)
        # Average of ~1.3 tokens per word for most tokenizers
        return int(len(words) * 1.3)

class ContentChunker:
    """Service for chunking content into manageable pieces."""
    
    def __init__(self):
        """Initialize the content chunker."""
        self.token_counter = TokenCounter()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
    
    def chunk_content(
        self, 
        content: str, 
        title: str = "", 
        headers: List[Dict[str, str]] = None,
        metadata: Dict[str, any] = None
    ) -> List[ContentChunk]:
        """Chunk content into overlapping segments.
        
        Args:
            content: Text content to chunk
            title: Title of the content
            headers: List of headers found in content
            metadata: Additional metadata
            
        Returns:
            List of ContentChunk objects
        """
        if not content:
            return []
        
        headers = headers or []
        metadata = metadata or {}
        
        logger.debug(f"Chunking content: {len(content)} characters, {len(headers)} headers")
        
        # Split content into sentences for better chunk boundaries
        sentences = self._split_into_sentences(content)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_number = 1
        
        # Track headers for context
        current_headers = self._find_relevant_headers(headers, content)
        
        for sentence in sentences:
            sentence_tokens = self.token_counter.count_tokens(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Create chunk from current content
                chunk = self._create_chunk(
                    chunk_number=chunk_number,
                    content=current_chunk.strip(),
                    title=title,
                    headers=current_headers,
                    metadata=metadata
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_content = self._get_overlap_content(current_chunk, self.chunk_overlap)
                current_chunk = overlap_content + " " + sentence
                current_tokens = self.token_counter.count_tokens(current_chunk)
                chunk_number += 1
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        # Create final chunk if there's remaining content
        if current_chunk.strip():
            chunk = self._create_chunk(
                chunk_number=chunk_number,
                content=current_chunk.strip(),
                title=title,
                headers=current_headers,
                metadata=metadata
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from content")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Clean text first
        text = clean_text(text)
        
        # Split on sentence boundaries
        # This is a simple approach - more sophisticated sentence splitting could be used
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _find_relevant_headers(self, headers: List[Dict[str, str]], content: str) -> List[Dict[str, str]]:
        """Find headers that are relevant to the content being chunked.
        
        Args:
            headers: List of all headers
            content: Content being chunked
            
        Returns:
            List of relevant headers
        """
        if not headers:
            return []
        
        relevant_headers = []
        
        for header in headers:
            # Simple approach: include all headers
            # More sophisticated: determine which headers apply to which content sections
            relevant_headers.append(header)
        
        return relevant_headers
    
    def _get_overlap_content(self, text: str, overlap_tokens: int) -> str:
        """Get overlap content from the end of a chunk.
        
        Args:
            text: Full text
            overlap_tokens: Number of tokens to overlap
            
        Returns:
            Overlap content
        """
        if overlap_tokens <= 0:
            return ""
        
        words = text.split()
        if len(words) <= overlap_tokens:
            return text
        
        # Take approximately the last N tokens worth of words
        overlap_words = int(overlap_tokens / 1.3)  # Reverse of token estimation
        overlap_words = max(1, min(overlap_words, len(words) - 1))
        
        return " ".join(words[-overlap_words:])
    
    def _create_chunk(
        self, 
        chunk_number: int, 
        content: str, 
        title: str, 
        headers: List[Dict[str, str]], 
        metadata: Dict[str, any]
    ) -> ContentChunk:
        """Create a ContentChunk object.
        
        Args:
            chunk_number: Sequential chunk number
            content: Chunk content
            title: Content title
            headers: Relevant headers
            metadata: Additional metadata
            
        Returns:
            ContentChunk object
        """
        token_count = self.token_counter.count_tokens(content)
        
        # Generate chunk title and summary
        chunk_title = self._generate_chunk_title(content, title, headers)
        chunk_summary = self._generate_chunk_summary(content)
        
        # Enhanced metadata
        chunk_metadata = {
            **metadata,
            'headers': headers,
            'word_count': len(content.split()),
            'character_count': len(content),
            'has_headers': len(headers) > 0
        }
        
        return ContentChunk(
            chunk_number=chunk_number,
            title=chunk_title,
            summary=chunk_summary,
            content=content,
            token_count=token_count,
            metadata=chunk_metadata
        )
    
    def _generate_chunk_title(
        self, 
        content: str, 
        page_title: str, 
        headers: List[Dict[str, str]]
    ) -> Optional[str]:
        """Generate a title for the chunk.
        
        Args:
            content: Chunk content
            page_title: Original page title
            headers: Relevant headers
            
        Returns:
            Generated title or None
        """
        # Use the most relevant header as chunk title
        if headers:
            # Find the highest level header (lowest number)
            relevant_header = min(headers, key=lambda h: h.get('level', 6))
            return relevant_header.get('text', page_title)
        
        # Fallback: use page title with chunk indicator
        return f"{page_title} (Part {1})" if page_title else None
    
    def _generate_chunk_summary(self, content: str) -> Optional[str]:
        """Generate a summary for the chunk.
        
        Args:
            content: Chunk content
            
        Returns:
            Generated summary or None
        """
        if not content:
            return None
        
        # Simple approach: take first sentence or first N characters
        sentences = self._split_into_sentences(content)
        if sentences:
            first_sentence = sentences[0]
            if len(first_sentence) > 200:
                return first_sentence[:200] + "..."
            return first_sentence
        
        # Fallback: truncate content
        if len(content) > 200:
            return content[:200] + "..."
        
        return content
    
    def chunk_page_content(
        self, 
        url: str, 
        title: str, 
        content: str, 
        headers: List[Dict[str, str]], 
        page_metadata: Dict[str, any]
    ) -> List[ContentChunk]:
        """Chunk content from a scraped page.
        
        Args:
            url: Page URL
            title: Page title
            content: Page content
            headers: Page headers
            page_metadata: Page metadata
            
        Returns:
            List of ContentChunk objects
        """
        metadata = {
            **page_metadata,
            'source_url': url,
            'source_title': title
        }
        
        return self.chunk_content(
            content=content,
            title=title,
            headers=headers,
            metadata=metadata
        )
    
    def get_chunk_stats(self, chunks: List[ContentChunk]) -> Dict[str, any]:
        """Get statistics about a list of chunks.
        
        Args:
            chunks: List of chunks
            
        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {
                'total_chunks': 0,
                'total_tokens': 0,
                'avg_tokens_per_chunk': 0,
                'min_tokens': 0,
                'max_tokens': 0
            }
        
        token_counts = [chunk.token_count for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': sum(token_counts),
            'avg_tokens_per_chunk': sum(token_counts) / len(token_counts),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'total_characters': sum(len(chunk.content) for chunk in chunks),
            'chunks_with_titles': sum(1 for chunk in chunks if chunk.title),
            'chunks_with_summaries': sum(1 for chunk in chunks if chunk.summary)
        }