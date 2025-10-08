"""Tests for web scraping functionality."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from aiohttp import ClientSession
from bs4 import BeautifulSoup

from app.services.scraper import WebScraper, ScrapedPage
from app.utils.helpers import normalize_url, is_valid_url

class TestWebScraper:
    """Test cases for WebScraper class."""
    
    @pytest.fixture
    def scraper(self):
        """Create a WebScraper instance for testing."""
        return WebScraper()
    
    def test_url_normalization(self):
        """Test URL normalization."""
        test_cases = [
            ("https://example.com/", "https://example.com"),
            ("https://example.com/path/", "https://example.com/path"),
            ("https://Example.COM/Path", "https://example.com/Path"),
            ("https://example.com/#fragment", "https://example.com"),
        ]
        
        for input_url, expected in test_cases:
            assert normalize_url(input_url) == expected
    
    def test_url_validation(self):
        """Test URL validation."""
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://sub.domain.com:8080/path?query=1"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "",
            "javascript:alert('xss')"
        ]
        
        for url in valid_urls:
            assert is_valid_url(url) == True
        
        for url in invalid_urls:
            assert is_valid_url(url) == False
    
    @pytest.mark.asyncio
    async def test_sitemap_parsing(self, scraper):
        """Test sitemap XML parsing."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page1</loc>
            </url>
            <url>
                <loc>https://example.com/page2</loc>
            </url>
        </urlset>"""
        
        urls = await scraper._parse_sitemap(sitemap_xml, "https://example.com")
        
        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
    
    @pytest.mark.asyncio
    async def test_sitemap_index_parsing(self, scraper):
        """Test sitemap index XML parsing."""
        sitemap_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap>
                <loc>https://example.com/sitemap1.xml</loc>
            </sitemap>
        </sitemapindex>"""
        
        # Mock the fetch_url method for nested sitemap
        nested_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/nested-page</loc></url>
        </urlset>"""
        
        with patch.object(scraper, '_fetch_url', return_value=(nested_sitemap, 200, {})):
            urls = await scraper._parse_sitemap(sitemap_index_xml, "https://example.com")
            assert "https://example.com/nested-page" in urls
    
    def test_content_extraction(self, scraper):
        """Test main content extraction from HTML."""
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <nav>Navigation</nav>
                <main>
                    <h1>Main Title</h1>
                    <p>This is the main content.</p>
                </main>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        content = scraper._extract_main_content(soup)
        
        assert "Main Title" in content
        assert "This is the main content." in content
        assert "Navigation" not in content
        assert "Footer content" not in content
    
    @pytest.mark.asyncio
    async def test_robots_txt_checking(self, scraper):
        """Test robots.txt compliance checking."""
        robots_txt = """User-agent: *
        Disallow: /admin/
        Disallow: /private/
        Allow: /public/
        """
        
        with patch.object(scraper, '_fetch_url', return_value=(robots_txt, 200, {})):
            # Test allowed URL
            allowed = await scraper._check_robots_txt("https://example.com", "https://example.com/public/page")
            assert allowed == True
            
            # Test disallowed URL
            disallowed = await scraper._check_robots_txt("https://example.com", "https://example.com/admin/page")
            assert disallowed == False
    
    @pytest.mark.asyncio
    async def test_page_scraping(self, scraper):
        """Test individual page scraping."""
        html_content = """
        <html>
            <head>
                <title>Test Page Title</title>
                <meta name="description" content="Test page description">
            </head>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>Article content goes here.</p>
                </article>
            </body>
        </html>
        """
        
        with patch.object(scraper, '_fetch_url', return_value=(html_content, 200, {'content-type': 'text/html'})):
            page = await scraper.scrape_page("https://example.com/test")
            
            assert page is not None
            assert page.title == "Test Page Title"
            assert page.summary == "Test page description"
            assert "Article Title" in page.content
            assert "Article content" in page.content
            assert page.metadata['http_status'] == 200
    
    @pytest.mark.asyncio
    async def test_low_value_page_filtering(self, scraper):
        """Test that low-value pages are filtered out."""
        # Test admin page (should be filtered)
        admin_html = "<html><head><title>Admin Login</title></head><body><p>Login required</p></body></html>"
        
        with patch.object(scraper, '_fetch_url', return_value=(admin_html, 200, {})):
            page = await scraper.scrape_page("https://example.com/admin/login")
            assert page is None  # Should be filtered out
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, scraper):
        """Test that rate limiting is applied."""
        # Mock multiple requests and measure timing
        import time
        
        with patch.object(scraper, '_fetch_url', return_value=("content", 200, {})):
            start_time = time.time()
            
            # Make multiple requests
            await scraper._fetch_url("https://example.com/1")
            await scraper._fetch_url("https://example.com/2")
            
            elapsed = time.time() - start_time
            
            # Should take at least 1 second due to rate limiting (1 req/sec)
            assert elapsed >= 1.0

class TestScrapingIntegration:
    """Integration tests for scraping functionality."""
    
    @pytest.mark.asyncio
    async def test_full_site_scraping_flow(self):
        """Test the complete site scraping workflow."""
        # Mock sitemap discovery
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>"""
        
        page_html = """
        <html>
            <head><title>Page {}</title></head>
            <body><main><p>Content for page {}</p></main></body>
        </html>
        """
        
        async def mock_fetch(url):
            if 'sitemap.xml' in url:
                return sitemap_xml, 200, {}
            elif 'page1' in url:
                return page_html.format(1, 1), 200, {}
            elif 'page2' in url:
                return page_html.format(2, 2), 200, {}
            else:
                return "", 404, {}
        
        async with WebScraper() as scraper:
            with patch.object(scraper, '_fetch_url', side_effect=mock_fetch):
                pages = await scraper.scrape_site("https://example.com")
                
                assert len(pages) == 2
                assert any("Content for page 1" in page.content for page in pages)
                assert any("Content for page 2" in page.content for page in pages)

if __name__ == "__main__":
    pytest.main([__file__])