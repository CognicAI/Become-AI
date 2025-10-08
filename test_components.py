"""Test script to verify the RAG system components."""
import asyncio
import sys
from pathlib import Path

async def test_components():
    """Test all major components of the RAG system."""
    print("🧪 Testing Become AI RAG System Components\n")
    
    try:
        # Test 1: Configuration
        print("1️⃣ Testing Configuration...")
        from app.utils.config import settings
        print(f"   ✅ Settings loaded: {settings.embedding_model}")
        
        # Test 2: Content Chunker
        print("\n2️⃣ Testing Content Chunker...")
        from app.services.chunker import ContentChunker
        chunker = ContentChunker()
        
        test_content = """
        This is a test document for the RAG system. It contains multiple sentences
        and paragraphs to test the chunking functionality. The chunker should split
        this content into manageable pieces while preserving context and meaning.
        
        This is the second paragraph of the test document. It continues with more
        content to ensure that the chunking algorithm works correctly with longer
        texts that exceed the token limits.
        """
        
        chunks = chunker.chunk_content(test_content.strip(), title="Test Document")
        print(f"   ✅ Created {len(chunks)} chunks from test content")
        if chunks:
            print(f"   📊 First chunk: {chunks[0].token_count} tokens")
        
        # Test 3: Helper Functions
        print("\n3️⃣ Testing Helper Functions...")
        from app.utils.helpers import normalize_url, is_valid_url, clean_text
        
        test_url = "https://example.com/path/"
        normalized = normalize_url(test_url)
        is_valid = is_valid_url(normalized)
        
        test_text = "   This is  a   messy    text   with   extra   spaces   "
        cleaned = clean_text(test_text)
        
        print(f"   ✅ URL normalization: {test_url} → {normalized}")
        print(f"   ✅ URL validation: {is_valid}")
        print(f"   ✅ Text cleaning: '{test_text}' → '{cleaned}'")
        
        # Test 4: Database Models
        print("\n4️⃣ Testing Database Models...")
        from app.models import ScrapeRequest, QueryRequest
        
        scrape_req = ScrapeRequest(
            site_name="Test Site",
            base_url="https://example.com",
            description="Test description"
        )
        
        query_req = QueryRequest(
            question="What is this about?",
            site_base_url="https://example.com"
        )
        
        print(f"   ✅ ScrapeRequest model: {scrape_req.site_name}")
        print(f"   ✅ QueryRequest model: {query_req.question}")
        
        # Test 5: FastAPI App
        print("\n5️⃣ Testing FastAPI Application...")
        from app.main import app
        print(f"   ✅ FastAPI app created: {app.title}")
        
        # Test 6: Embedding Service (without loading the model)
        print("\n6️⃣ Testing Embedding Service...")
        from app.services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        print(f"   ✅ Embedding service initialized: {embedding_service.model_name}")
        print(f"   📐 Expected dimension: {embedding_service.dimension}")
        
        # Test 7: LLM Service (without connecting)
        print("\n7️⃣ Testing LLM Service...")
        from app.services.llm import LLMService, ChunkContext
        llm_service = LLMService()
        
        # Test prompt creation
        test_contexts = [
            ChunkContext(
                chunk_id=1,
                content="This is test content about artificial intelligence.",
                title="AI Overview",
                url="https://example.com/ai",
                similarity_score=0.95
            )
        ]
        
        prompt = llm_service.create_rag_prompt("What is AI?", test_contexts)
        print(f"   ✅ LLM service initialized: {llm_service.model_name}")
        print(f"   📝 Generated prompt length: {len(prompt)} characters")
        
        # Test 8: Web Scraper (without making requests)
        print("\n8️⃣ Testing Web Scraper...")
        from app.services.scraper import WebScraper
        scraper = WebScraper()
        print(f"   ✅ Web scraper initialized with rate limit: {scraper.rate_limiter.max_rate} req/s")
        
        print("\n🎉 All component tests passed!")
        print("\n📋 System Summary:")
        print(f"   • Tech Stack: FastAPI + PostgreSQL + pgvector + Phi-3 Mini")
        print(f"   • Embedding Model: {settings.embedding_model} ({settings.embedding_dimension}D)")
        print(f"   • Chunk Size: {settings.chunk_size} tokens (overlap: {settings.chunk_overlap})")
        print(f"   • API Endpoints: Scraping + Query with SSE streaming")
        print(f"   • Rate Limiting: {settings.scraping_rate_limit} req/s")
        
        print("\n🚀 Ready to start the server with: python start.py")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main function to run tests."""
    success = asyncio.run(test_components())
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()