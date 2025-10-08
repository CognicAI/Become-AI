"""Helper utilities for the RAG system."""
import re
import hashlib
import asyncio
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urljoin, urlparse, urlunparse
from datetime import datetime, timezone
import time

def normalize_url(url: str) -> str:
    """Normalize URL by removing trailing slashes and fragments.
    
    Args:
        url: Raw URL string
        
    Returns:
        Normalized URL string
    """
    parsed = urlparse(url)
    # Remove fragment and trailing slash from path
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    
    # Reconstruct URL without fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        path,
        parsed.params,
        parsed.query,
        ''  # No fragment
    ))
    
    return normalized

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid and accessible.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False

def extract_domain(url: str) -> str:
    """Extract domain from URL.
    
    Args:
        url: URL string
        
    Returns:
        Domain name
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()

def generate_job_id(site_url: str) -> str:
    """Generate a unique job ID for scraping tasks.
    
    Args:
        site_url: Base URL of the site being scraped
        
    Returns:
        Unique job ID string
    """
    timestamp = str(int(time.time() * 1000))  # Milliseconds
    url_hash = hashlib.md5(site_url.encode()).hexdigest()[:8]
    return f"job_{timestamp}_{url_hash}"

def clean_text(text: str) -> str:
    """Clean and normalize text content.
    
    Args:
        text: Raw text content
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text

def extract_headers(html_content: str) -> List[Dict[str, str]]:
    """Extract headers (h1-h6) from HTML content.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        List of header dictionaries with level and text
    """
    import re
    headers = []
    
    # Match h1-h6 tags
    header_pattern = r'<h([1-6])[^>]*>(.*?)</h[1-6]>'
    matches = re.findall(header_pattern, html_content, re.IGNORECASE | re.DOTALL)
    
    for level, text in matches:
        # Clean the header text
        clean_text_content = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
        clean_text_content = clean_text(clean_text_content)
        
        if clean_text_content:
            headers.append({
                'level': int(level),
                'text': clean_text_content
            })
    
    return headers

def is_low_value_page(url: str, title: str = "", content: str = "") -> bool:
    """Determine if a page is low-value and should be skipped.
    
    Args:
        url: Page URL
        title: Page title
        content: Page content
        
    Returns:
        True if page should be skipped, False otherwise
    """
    url_lower = url.lower()
    title_lower = title.lower()
    
    # Skip common low-value paths
    skip_patterns = [
        '/login', '/signin', '/signup', '/register',
        '/admin', '/wp-admin', '/dashboard',
        '/search', '/results',
        '/cart', '/checkout', '/account',
        '/404', '/error', '/maintenance',
        '/.well-known', '/robots.txt', '/sitemap',
        '/feed', '/rss', '/api/',
        '/download', '/pdf', '/doc', '/docx'
    ]
    
    for pattern in skip_patterns:
        if pattern in url_lower:
            return True
    
    # Skip based on title patterns
    skip_title_patterns = [
        'login', 'sign in', 'sign up', 'register',
        'admin', 'dashboard', 'account',
        '404', 'not found', 'error',
        'search results', 'cart', 'checkout'
    ]
    
    for pattern in skip_title_patterns:
        if pattern in title_lower:
            return True
    
    # Skip if content is too short (likely not meaningful)
    if len(content.strip()) < 100:
        return True
    
    return False

def calculate_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    import math
    
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length")
    
    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    # Calculate cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)
    
    # Ensure result is between 0 and 1
    return max(0.0, min(1.0, similarity))

def get_current_timestamp() -> datetime:
    """Get current UTC timestamp.
    
    Returns:
        Current datetime in UTC
    """
    return datetime.now(timezone.utc)

async def run_with_timeout(coro, timeout_seconds: float):
    """Run an async coroutine with a timeout.
    
    Args:
        coro: Coroutine to run
        timeout_seconds: Timeout in seconds
        
    Returns:
        Result of the coroutine
        
    Raises:
        asyncio.TimeoutError: If operation times out
    """
    return await asyncio.wait_for(coro, timeout=timeout_seconds)

class RateLimiter:
    """Simple rate limiter for controlling request frequency."""
    
    def __init__(self, max_rate: float):
        """Initialize rate limiter.
        
        Args:
            max_rate: Maximum requests per second
        """
        self.max_rate = max_rate
        self.min_interval = 1.0 / max_rate if max_rate > 0 else 0
        self.last_request = 0.0
    
    async def acquire(self):
        """Acquire permission to make a request."""
        now = time.time()
        elapsed = now - self.last_request
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            await asyncio.sleep(sleep_time)
        
        self.last_request = time.time()

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"