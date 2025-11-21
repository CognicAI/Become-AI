"""Migration script to add is_metadata_updated column to site_pages table."""
import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Get database URL
database_url = os.getenv("DATABASE_URL")
# Convert from SQLAlchemy format to psycopg2 format
if database_url.startswith("postgresql+psycopg2://"):
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql://")

# Connect to database
conn = psycopg2.connect(database_url)
cursor = conn.cursor()

try:
    # Add column if it doesn't exist
    cursor.execute("""
        ALTER TABLE site_pages 
        ADD COLUMN IF NOT EXISTS is_metadata_updated BOOLEAN DEFAULT FALSE;
    """)
    
    conn.commit()
    print("✅ Successfully added is_metadata_updated column to site_pages table")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
    
finally:
    cursor.close()
    conn.close()
