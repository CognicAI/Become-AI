"""Test database connection and setup for the RAG system."""
import os
import sys
from pathlib import Path
import subprocess

def test_database_connection():
    """Test PostgreSQL database connection."""
    print("🔍 Testing database connection...")
    
    try:
        # Import database modules
        from app.db.db import test_connection, DATABASE_URL
        from app.utils.config import settings
        
        print(f"📍 Database URL: {DATABASE_URL}")
        print(f"🔗 Connecting to database...")
        
        # Test connection
        if test_connection():
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure to run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def check_postgresql_running():
    """Check if PostgreSQL is running locally."""
    print("\n🔍 Checking if PostgreSQL is running...")
    
    # Import settings to get the correct database URL
    try:
        from app.utils.config import settings
        db_url = settings.database_url
        
        # Extract port from database URL
        import re
        match = re.search(r':(\d+)/', db_url)
        port = match.group(1) if match else "5432"
        
        print(f"📍 Checking PostgreSQL on port {port}...")
        
    except Exception as e:
        print(f"⚠️  Could not load config: {e}")
        port = "5432"
    
    try:
        # Try to connect using psql command
        result = subprocess.run(
            ["psql", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ PostgreSQL client found: {result.stdout.strip()}")
            
            # Try to connect to default database with correct port
            try:
                result = subprocess.run(
                    ["psql", "-h", "localhost", "-U", "postgres", "-p", port, "-c", "SELECT version();"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print(f"✅ PostgreSQL server is running and accessible on port {port}")
                    return True
                else:
                    print(f"❌ PostgreSQL server not accessible on port {port}")
                    print(f"Error: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("❌ PostgreSQL connection timed out")
                return False
                
        else:
            print("❌ PostgreSQL client (psql) not found in PATH")
            return False
            
    except FileNotFoundError:
        print("❌ PostgreSQL client (psql) not installed or not in PATH")
        return False
    except Exception as e:
        print(f"❌ Error checking PostgreSQL: {e}")
        return False

def check_pgvector_extension():
    """Check if pgvector extension is available."""
    print("\n🔍 Checking pgvector extension...")
    
    try:
        import psycopg2
        from app.utils.config import settings
        
        # Parse database URL
        db_url = settings.database_url
        
        # Extract connection parameters (simplified)
        if "postgresql+psycopg2://" in db_url:
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check if pgvector extension exists
        cursor.execute("SELECT * FROM pg_available_extensions WHERE name = 'vector';")
        result = cursor.fetchone()
        
        if result:
            print("✅ pgvector extension is available")
            
            # Check if it's installed
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            installed = cursor.fetchone()
            
            if installed:
                print("✅ pgvector extension is installed")
            else:
                print("⚠️  pgvector extension available but not installed")
                print("💡 Run: CREATE EXTENSION IF NOT EXISTS vector;")
                
        else:
            print("❌ pgvector extension not available")
            print("💡 Install pgvector: https://github.com/pgvector/pgvector")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking pgvector: {e}")
        return False

def create_database_if_needed():
    """Create database if it doesn't exist."""
    print("\n🔍 Checking if database exists...")
    
    try:
        import psycopg2
        from app.utils.config import settings
        
        # Parse connection details
        db_url = settings.database_url
        
        # Try to connect to the specific database
        try:
            conn = psycopg2.connect(db_url.replace("postgresql+psycopg2://", "postgresql://"))
            print("✅ Target database exists and is accessible")
            conn.close()
            return True
            
        except psycopg2.OperationalError as e:
            if "does not exist" in str(e):
                print("⚠️  Target database does not exist")
                print("💡 Creating database...")
                
                # Connect to postgres database to create the target database
                import re
                match = re.match(r'postgresql\+psycopg2://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', settings.database_url)
                if match:
                    user, password, host, port, dbname = match.groups()
                    
                    # Connect to postgres database
                    postgres_url = f"postgresql://{user}:{password}@{host}:{port}/postgres"
                    conn = psycopg2.connect(postgres_url)
                    conn.autocommit = True
                    cursor = conn.cursor()
                    
                    # Create database
                    cursor.execute(f'CREATE DATABASE "{dbname}";')
                    print(f"✅ Created database: {dbname}")
                    
                    cursor.close()
                    conn.close()
                    return True
                else:
                    print("❌ Could not parse database URL")
                    return False
            else:
                print(f"❌ Database connection error: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def setup_database_schema():
    """Set up database schema."""
    print("\n🔍 Setting up database schema...")
    
    try:
        from app.db.db import init_db
        
        init_db()
        print("✅ Database schema initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up schema: {e}")
        print("💡 You may need to run the schema.sql file manually")
        return False

def print_setup_instructions():
    """Print setup instructions for different scenarios."""
    print("\n" + "="*60)
    print("🚀 DATABASE SETUP INSTRUCTIONS")
    print("="*60)
    
    print("\n📋 Option 1: Docker (Recommended for testing)")
    print("docker run --name postgres-pgvector \\")
    print("  -e POSTGRES_PASSWORD=password \\")
    print("  -e POSTGRES_DB=become_ai \\")
    print("  -p 5432:5432 \\")
    print("  -d pgvector/pgvector:pg15")
    print("\n# Then update your .env file:")
    print("DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/become_ai")
    
    print("\n📋 Option 2: Local PostgreSQL Installation")
    print("1. Install PostgreSQL: https://www.postgresql.org/download/")
    print("2. Install pgvector extension: https://github.com/pgvector/pgvector")
    print("3. Create database:")
    print("   createdb -U postgres become_ai")
    print("4. Connect and enable extension:")
    print("   psql -U postgres -d become_ai -c 'CREATE EXTENSION IF NOT EXISTS vector;'")
    
    print("\n📋 Option 3: Cloud PostgreSQL")
    print("1. Set up PostgreSQL on cloud provider (AWS RDS, Google Cloud SQL, etc.)")
    print("2. Enable pgvector extension")
    print("3. Update DATABASE_URL in .env file")
    
    print("\n🔧 After database setup:")
    print("1. Run this script again: python test_db_connection.py")
    print("2. Start the application: python start.py")

def main():
    """Main function to test database setup."""
    print("🧪 Become AI RAG System - Database Connection Test")
    print("="*60)
    
    # Check if we're in the right directory
    if not Path("app/main.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Check PostgreSQL
    postgres_running = check_postgresql_running()
    
    # Test database connection
    db_connected = test_database_connection()
    
    if db_connected:
        print("\n🎉 Database connection successful!")
        
        # Check pgvector
        check_pgvector_extension()
        
        # Setup schema
        setup_database_schema()
        
        print("\n✅ Database setup complete!")
        print("🚀 You can now run: python start.py")
        
    else:
        print("\n❌ Database connection failed!")
        
        if not postgres_running:
            print("\n💡 PostgreSQL doesn't appear to be running.")
        
        print_setup_instructions()
        
        print("\n🔧 Quick Docker setup:")
        print("docker run --name postgres-pgvector -e POSTGRES_PASSWORD=password -e POSTGRES_DB=become_ai -p 5432:5432 -d pgvector/pgvector:pg15")
        print("\nThen update .env with: DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/become_ai")

if __name__ == "__main__":
    main()