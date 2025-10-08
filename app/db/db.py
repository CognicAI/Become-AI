"""Database connection and session management."""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg2://user:password@localhost:5432/become_ai"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for ORM models
Base = declarative_base()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database with schema and extensions."""
    try:
        with engine.connect() as conn:
            # Enable pgvector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # Enable pgcrypto for gen_random_uuid()
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
            conn.commit()
            logger.info("Database extensions enabled successfully")
            
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def test_connection():
    """Test database connection."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

async def get_db_async():
    """Async database session for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()