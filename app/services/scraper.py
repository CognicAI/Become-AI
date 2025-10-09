"""Web scraping service with sitemap discovery and content extraction."""
# type: ignore
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from typing import List, Dict, Optional, Set, Tuple, Any
import logging
from dataclasses import dataclass

from ..utils.helpers import (
    normalize_url, is_valid_url, extract_domain, 
    clean_text, extract_headers, is_low_value_page, RateLimiter
)
from ..utils.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ScrapedPage:
    """Container for scraped page data."""
    url: str
    title: str
    content: str
    summary: str
    headers: List[Dict[str, str]]
    metadata: Dict[str, Any]

class WebScraper:
    """Web scraper with sitemap discovery and content extraction."""
    
    # Cache of RobotFileParser or None if no robots.txt
    # robots_cache will be initialized in __init__

    def __init__(self):
        # Initialize scraper
        self.rate_limiter = RateLimiter(settings.scraping_rate_limit)
        self.session: Optional[aiohttp.ClientSession] = None
        # Cache of RobotFileParser or None if no robots.txt
        self.robots_cache = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=settings.scraping_timeout)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': settings.scraping_user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _fetch_url(self, url: str) -> Tuple[str, int, Dict[str, str]]:
        """Fetch content from a URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (content, status_code, headers)
            
        Raises:
            aiohttp.ClientError: If request fails
        """
        assert self.session is not None, "Session not initialized"
        await self.rate_limiter.acquire()

        async with self.session.get(url) as response:
            content = await response.text()
            headers = dict(response.headers)
            return content, response.status, headers
    
    async def _check_robots_txt(self, base_url: str, url: str) -> bool:
        """Check if URL is allowed by robots.txt.
        
        Args:
            base_url: Base URL of the site
            url: Specific URL to check
            
        Returns:
            True if URL is allowed, False otherwise
        """
        domain = extract_domain(base_url)
        
        if domain not in self.robots_cache:
            robots_url = urljoin(base_url, '/robots.txt')
            
            try:
                content, status, _ = await self._fetch_url(robots_url)
                if status == 200:
                    rp = RobotFileParser()
                    rp.set_url(robots_url)
                    rp.read()
                    self.robots_cache[domain] = rp
                else:
                    # If no robots.txt, allow all
                    self.robots_cache[domain] = None
            except Exception as e:
                logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
                self.robots_cache[domain] = None
        
        robots = self.robots_cache[domain]
        if robots is None:
            return True
        
        return robots.can_fetch(settings.scraping_user_agent, url)
    
    async def discover_sitemap_urls(self, base_url: str) -> List[str]:
        """Discover sitemap URLs for a website.
        
        Args:
            base_url: Base URL of the website
            
        Returns:
            List of URLs found in sitemaps
        """
        sitemap_urls = []
        domain = extract_domain(base_url)
        
        # Common sitemap locations
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml', 
            '/sitemap/sitemap.xml',
            '/sitemaps/sitemap.xml'
        ]
        
        logger.info(f"Discovering sitemaps for {domain}")
        
        for path in sitemap_paths:
            sitemap_url = urljoin(base_url, path)
            
            try:
                content, status, _ = await self._fetch_url(sitemap_url)
                if status == 200:
                    logger.info(f"Found sitemap: {sitemap_url}")
                    urls = await self._parse_sitemap(content, base_url)
                    sitemap_urls.extend(urls)
                    break  # Use first sitemap found
                    
            except Exception as e:
                logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")
                continue
        
        if not sitemap_urls:
            logger.info(f"No sitemaps found for {domain}, will use fallback crawling")
        
        return list(set(sitemap_urls))  # Remove duplicates
    
    async def _parse_sitemap(self, xml_content: str, base_url: str) -> List[str]:
        """Parse sitemap XML and extract URLs.
        
        Args:
            xml_content: XML content of sitemap
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of URLs from sitemap
        """
        urls = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Handle sitemap index files
            if 'sitemapindex' in root.tag:
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None and loc.text:
                        # Recursively parse nested sitemaps
                        try:
                            content, status, _ = await self._fetch_url(loc.text)
                            if status == 200:
                                nested_urls = await self._parse_sitemap(content, base_url)
                                urls.extend(nested_urls)
                        except Exception as e:
                            logger.warning(f"Failed to parse nested sitemap {loc.text}: {e}")
            
            # Handle regular sitemap files
            else:
                for url_el in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = url_el.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None and loc.text:
                        urls.append(loc.text)
        
        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML: {e}")
        
        # Filter and normalize URLs
        filtered_urls = []
        for url in urls:
            normalized = normalize_url(url)
            if is_valid_url(normalized) and extract_domain(normalized) == extract_domain(base_url):
                filtered_urls.append(normalized)
        
        logger.info(f"Extracted {len(filtered_urls)} URLs from sitemap")
        return filtered_urls
    
    async def crawl_site_fallback(self, base_url: str, max_pages: int = 100) -> List[str]:
        """Fallback crawling method when no sitemap is available.
        
        Args:
            base_url: Base URL to start crawling from
            max_pages: Maximum number of pages to discover
            
        Returns:
            List of discovered URLs
        """
        discovered_urls = set()
        to_crawl = {normalize_url(base_url)}
        crawled = set()
        
        logger.info(f"Starting fallback crawling from {base_url}")
        
        while to_crawl and len(discovered_urls) < max_pages:
            current_url = to_crawl.pop()
            
            if current_url in crawled:
                continue
                
            crawled.add(current_url)
            
            # Check robots.txt
            if not await self._check_robots_txt(base_url, current_url):
                logger.debug(f"URL blocked by robots.txt: {current_url}")
                continue
            
            try:
                content, status, _ = await self._fetch_url(current_url)
                if status == 200:
                    discovered_urls.add(current_url)
                    
                    # Extract links for further crawling
                    soup = BeautifulSoup(content, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        # Skip non-string hrefs
                        if not isinstance(href, str):
                            continue
                        absolute_url = urljoin(current_url, href)
                        normalized = normalize_url(absolute_url)
                        
                        # Only crawl URLs from the same domain
                        if (extract_domain(normalized) == extract_domain(base_url) and
                            normalized not in crawled and
                            len(discovered_urls) < max_pages):
                            to_crawl.add(normalized)
                            
            except Exception as e:
                logger.warning(f"Failed to crawl {current_url}: {e}")
                continue
        
        logger.info(f"Fallback crawling discovered {len(discovered_urls)} URLs")
        return list(discovered_urls)
    
    async def scrape_page(self, url: str) -> Optional[ScrapedPage]:
        """Scrape content from a single page.
        
        Args:
            url: URL to scrape
            
        Returns:
            ScrapedPage object or None if scraping failed
        """
        try:
            content, status, headers = await self._fetch_url(url)
            
            if status != 200:
                logger.warning(f"HTTP {status} for {url}")
                return None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            title = clean_text(title_tag.get_text()) if title_tag else "Untitled"
            
            # Extract meta description for summary
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            summary = ""
            if meta_desc is not None:
                content_attr = meta_desc.get('content')
                if isinstance(content_attr, str) and content_attr:
                    summary = clean_text(content_attr)
            
            # Extract main content
            main_content = self._extract_main_content(soup)
            content_text = clean_text(main_content)
            
            # Check if this is a low-value page
            if is_low_value_page(url, title, content_text):
                logger.debug(f"Skipping low-value page: {url}")
                return None
            
            # Extract headers
            headers_list = extract_headers(str(soup))
            
            # Create metadata
            metadata = {
                'http_status': status,
                'content_length': len(content),
                'content_type': headers.get('content-type', ''),
                'last_modified': headers.get('last-modified', ''),
                'headers_count': len(headers_list),
                'word_count': len(content_text.split()) if content_text else 0
            }
            
            return ScrapedPage(
                url=url,
                title=title,
                content=content_text,
                summary=summary,
                headers=headers_list,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML soup.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Extracted text content
        """
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                           'aside', 'noscript', 'iframe']):
            element.decompose()
        
        # Try to find main content areas
        main_selectors = [
            'main',
            'article', 
            '[role="main"]',
            '.content',
            '.main-content',
            '#content',
            '#main'
        ]
        
        content_text = ""
        
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                content_text = ' '.join(elem.get_text(separator=' ') for elem in elements)
                break
        
        # Fallback: get all text from body
        if not content_text:
            body = soup.find('body')
            if body:
                content_text = body.get_text(separator=' ')
            else:
                content_text = soup.get_text(separator=' ')
        
        return content_text
    
    async def scrape_site(self, base_url: str, max_pages: int = 1000) -> List[ScrapedPage]:
        """Scrape an entire website.
        
        Args:
            base_url: Base URL of the website
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of successfully scraped pages
        """
        logger.info(f"Starting site scrape for {base_url}")
        
        # Discover URLs
        sitemap_urls = await self.discover_sitemap_urls(base_url)
        # Determine URL limit based on test mode
        if settings.scraping_test_mode:
            url_limit = settings.scraping_test_url_limit
        else:
            url_limit = max_pages

        if sitemap_urls:
            # Limit number of URLs based on mode
            urls_to_scrape = sitemap_urls[:url_limit]
        else:
            # Fallback to crawling with limit
            urls_to_scrape = await self.crawl_site_fallback(base_url, url_limit)
        
        logger.info(f"Found {len(urls_to_scrape)} URLs to scrape")
        
        # Scrape pages
        scraped_pages = []
        
        for i, url in enumerate(urls_to_scrape):
            logger.info(f"Scraping page {i+1}/{len(urls_to_scrape)}: {url}")
            
            # Check robots.txt
            if not await self._check_robots_txt(base_url, url):
                logger.debug(f"Skipping URL blocked by robots.txt: {url}")
                continue
            
            page = await self.scrape_page(url)
            if page:
                scraped_pages.append(page)
                logger.debug(f"Successfully scraped: {url}")
            else:
                logger.warning(f"Failed to scrape: {url}")
        
        logger.info(f"Successfully scraped {len(scraped_pages)} pages from {base_url}")
        return scraped_pages