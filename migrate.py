from app.db.db import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    try:
        with engine.connect() as conn:
            logger.info("Applying migration...")
            conn.execute(text("ALTER TABLE page_chunks ADD COLUMN IF NOT EXISTS is_metadata_updated BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            logger.info("Migration applied successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
