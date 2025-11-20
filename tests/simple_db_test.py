"""Simple database connection test without importing the full app."""
import os
import sys
from pathlib import Path

# Add the current directory to path so we can import app modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("🧪 Simple Database Connection Test")
print("="*50)

# Check if .env file exists
env_file = current_dir / ".env"
print(f"📍 Looking for .env file at: {env_file}")
print(f"📍 .env file exists: {env_file.exists()}")

if env_file.exists():
    print(f"📍 .env file size: {env_file.stat().st_size} bytes")
    
    # Read first few lines to verify content
    with open(env_file, 'r') as f:
        lines = f.readlines()[:10]
    print("\n📄 First 10 lines of .env file:")
    for i, line in enumerate(lines, 1):
        if "DATABASE_URL" in line:
            print(f"  {i}: {line.strip()} ← DATABASE_URL FOUND")
        else:
            print(f"  {i}: {line.strip()}")

print(f"\n🔍 Current working directory: {os.getcwd()}")

# Try to load environment variables manually
from dotenv import load_dotenv
print(f"\n🔧 Loading .env file...")
load_dotenv(env_file)

# Check what DATABASE_URL is set to
db_url = os.getenv("DATABASE_URL")
print(f"📍 DATABASE_URL from environment: {db_url}")

# Now try to import and use settings
print(f"\n🔧 Testing app config...")
try:
    from app.utils.config import settings
    print(f"📍 DATABASE_URL from settings: {settings.database_url}")
    
    # Test actual database connection
    print(f"\n🔧 Testing database connection...")
    import psycopg2
    
    try:
        conn = psycopg2.connect(settings.database_url.replace("postgresql+psycopg2://", "postgresql://"))
        print("✅ Database connection successful!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📍 PostgreSQL version: {version}")
        
        # Check if pgvector is installed
        cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
        vector_ext = cursor.fetchone()
        if vector_ext:
            print("✅ pgvector extension is installed")
        else:
            print("⚠️  pgvector extension not installed")
            print("💡 Run: CREATE EXTENSION IF NOT EXISTS vector;")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database setup is complete and working!")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        
except Exception as e:
    print(f"❌ Error importing config: {e}")