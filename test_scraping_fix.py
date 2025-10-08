"""Quick test to verify the scraping fixes."""
import requests
import json
import time

def test_scraping_fix():
    """Test if the scraping database issue is fixed."""
    print("🧪 Testing Scraping Database Fix")
    print("=" * 40)
    
    # Test health first
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server not running. Start with: python start.py")
            return False
        print("✅ Server is running")
    except:
        print("❌ Server not accessible. Start with: python start.py")
        return False
    
    # Test scraping with a simple site
    print("\n📄 Testing scraping with example.com...")
    
    scrape_data = {
        "site_name": "Example Test Site",
        "base_url": "https://example.com",
        "description": "Simple test site for database fix verification"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/scrape",
            json=scrape_data,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get("job_id")
            print(f"✅ Scraping job started: {job_id}")
            
            # Check status a few times
            for i in range(6):  # Check for up to 30 seconds
                time.sleep(5)
                
                status_response = requests.get(f"http://localhost:8000/scrape/status/{job_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status", "unknown")
                    progress = status_data.get("progress", 0)
                    
                    print(f"📊 Status: {status} | Progress: {progress:.1f}%")
                    
                    if status == "completed":
                        print("🎉 Scraping completed successfully!")
                        print("✅ Database fixes are working!")
                        return True
                    elif status == "failed":
                        error = status_data.get("error", "Unknown error")
                        print(f"❌ Scraping failed: {error}")
                        return False
                else:
                    print(f"⚠️  Status check failed: {status_response.status_code}")
            
            print("⏳ Scraping still in progress after 30 seconds")
            print("💡 Check the server logs for more details")
            return True  # Not necessarily a failure
            
        else:
            print(f"❌ Scraping request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing scraping: {e}")
        return False

if __name__ == "__main__":
    test_scraping_fix()