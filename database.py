import os
import asyncio
from typing import Optional
import asyncpg
from supabase import create_client, Client
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gmqraxtnttopkkflrhla.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdtcXJheHRudHRvcGtrZmxyaGxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzU0MDU3ODQsImV4cCI6MjA1MDk4MTc4NH0.GobJJmDBwEU6iu3iRaGIi8DEvTHy6cGu7gXRUm7uJnU")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQLAlchemy engine for direct SQL queries
engine = None
SessionLocal = None

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("✅ SQLAlchemy engine initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize SQLAlchemy engine: {e}")

# Global connection pool
connection_pool: Optional[asyncpg.Pool] = None

async def init_db_pool():
    """Initialize the asyncpg connection pool"""
    global connection_pool
    
    if not DATABASE_URL:
        logger.warning("⚠️ DATABASE_URL not found, skipping pool initialization")
        return
    
    try:
        connection_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        logger.info("✅ Database connection pool initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize connection pool: {e}")

async def close_db_pool():
    """Close the database connection pool"""
    global connection_pool
    
    if connection_pool:
        await connection_pool.close()
        logger.info("✅ Database connection pool closed")

# SYNCHRONOUS DATABASE CONNECTION (for existing code compatibility)
def get_db_connection():
    """
    Get a synchronous database connection using SQLAlchemy
    Returns a SQLAlchemy Session object
    """
    if not SessionLocal:
        logger.error("❌ Database not initialized. Check DATABASE_URL.")
        raise Exception("Database connection not available")
    
    try:
        db_session = SessionLocal()
        logger.info("✅ Database session created")
        return db_session
    except Exception as e:
        logger.error(f"❌ Failed to create database session: {e}")
        raise

def get_db_session():
    """
    Dependency function for FastAPI to get database session
    """
    db = get_db_connection()
    try:
        yield db
    finally:
        db.close()

# ASYNC DATABASE CONNECTION (for new async code)
async def get_async_db_connection():
    """
    Get an async database connection from the pool
    """
    global connection_pool
    
    if not connection_pool:
        await init_db_pool()
    
    if not connection_pool:
        raise Exception("Database connection pool not available")
    
    try:
        async with connection_pool.acquire() as connection:
            yield connection
    except Exception as e:
        logger.error(f"❌ Failed to acquire database connection: {e}")
        raise

# SUPABASE CLIENT FUNCTIONS
def get_supabase_client() -> Client:
    """Get the Supabase client"""
    return supabase

# DATABASE UTILITY FUNCTIONS
async def execute_query(query: str, params: tuple = None):
    """
    Execute a raw SQL query using asyncpg
    """
    global connection_pool
    
    if not connection_pool:
        await init_db_pool()
    
    if not connection_pool:
        raise Exception("Database connection pool not available")
    
    try:
        async with connection_pool.acquire() as connection:
            if params:
                result = await connection.fetch(query, *params)
            else:
                result = await connection.fetch(query)
            return result
    except Exception as e:
        logger.error(f"❌ Failed to execute query: {e}")
        raise

def execute_sync_query(query: str, params: dict = None):
    """
    Execute a raw SQL query using SQLAlchemy (synchronous)
    """
    if not engine:
        raise Exception("Database engine not available")
    
    try:
        with engine.connect() as connection:
            if params:
                result = connection.execute(text(query), params)
            else:
                result = connection.execute(text(query))
            return result.fetchall()
    except Exception as e:
        logger.error(f"❌ Failed to execute sync query: {e}")
        raise

# SUPABASE HELPER FUNCTIONS
def supabase_select(table: str, columns: str = "*", filters: dict = None):
    """
    Helper function for Supabase SELECT queries
    """
    try:
        query = supabase.table(table).select(columns)
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"❌ Supabase select error: {e}")
        raise

def supabase_insert(table: str, data: dict):
    """
    Helper function for Supabase INSERT queries
    """
    try:
        result = supabase.table(table).insert(data).execute()
        return result.data
    except Exception as e:
        logger.error(f"❌ Supabase insert error: {e}")
        raise

def supabase_update(table: str, data: dict, filters: dict):
    """
    Helper function for Supabase UPDATE queries
    """
    try:
        query = supabase.table(table).update(data)
        
        for key, value in filters.items():
            query = query.eq(key, value)
        
        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"❌ Supabase update error: {e}")
        raise

def supabase_delete(table: str, filters: dict):
    """
    Helper function for Supabase DELETE queries
    """
    try:
        query = supabase.table(table)
        
        for key, value in filters.items():
            query = query.eq(key, value)
        
        result = query.delete().execute()
        return result.data
    except Exception as e:
        logger.error(f"❌ Supabase delete error: {e}")
        raise

# DATABASE HEALTH CHECK
async def check_database_health():
    """
    Check if database connections are working
    """
    health_status = {
        "supabase": False,
        "asyncpg": False,
        "sqlalchemy": False
    }
    
    # Test Supabase connection
    try:
        result = supabase.table("person_records").select("staff_id").limit(1).execute()
        health_status["supabase"] = True
        logger.info("✅ Supabase connection healthy")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
    
    # Test asyncpg connection
    try:
        if connection_pool:
            async with connection_pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
            health_status["asyncpg"] = True
            logger.info("✅ AsyncPG connection healthy")
    except Exception as e:
        logger.error(f"❌ AsyncPG connection failed: {e}")
    
    # Test SQLAlchemy connection
    try:
        if engine:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            health_status["sqlalchemy"] = True
            logger.info("✅ SQLAlchemy connection healthy")
    except Exception as e:
        logger.error(f"❌ SQLAlchemy connection failed: {e}")
    
    return health_status

# Initialize database on module import
async def initialize_database():
    """Initialize all database connections"""
    logger.info("🔄 Initializing database connections...")
    await init_db_pool()
    health = await check_database_health()
    logger.info(f"📊 Database health: {health}")

# Cleanup function
async def cleanup_database():
    """Cleanup database connections"""
    logger.info("🔄 Cleaning up database connections...")
    await close_db_pool()

# Export all functions
__all__ = [
    'get_db_connection',
    'get_db_session', 
    'get_async_db_connection',
    'get_supabase_client',
    'execute_query',
    'execute_sync_query',
    'supabase_select',
    'supabase_insert',
    'supabase_update',
    'supabase_delete',
    'check_database_health',
    'initialize_database',
    'cleanup_database',
    'supabase'
]