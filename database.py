import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create SQLAlchemy engine
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    logger.info("✅ SQLAlchemy engine initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize database engine: {str(e)}")
    raise

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI dependency injection.
    Creates a new SQLAlchemy SessionLocal for each request and closes it when done.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database session: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection() -> bool:
    """
    Test database connectivity
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {str(e)}")
        return False

def init_db():
    """
    Initialize database tables (if needed)
    This will create all tables defined in your models
    """
    try:
        # Import all models here to ensure they are registered with Base
        from models.person_record import PersonRecord
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database tables: {str(e)}")
        raise

# Test connection on module import
if __name__ == "__main__":
    test_connection()
else:
    # Test connection when imported
    try:
        test_connection()
    except Exception as e:
        logger.warning(f"Database connection test failed on import: {str(e)}")
