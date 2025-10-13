#!/usr/bin/env python3
"""
RelishAgro Backend Startup Script
Handles graceful startup with error diagnostics
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY", 
        "ALGORITHM"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def check_database_connection():
    """Test database connectivity before starting the server"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL not found")
            return False
        
        logger.info(f"🔍 Testing database connection...")
        
        # Test with supabase client
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL", "https://gmqraxtnttopkkflrhla.supabase.co")
        supabase_key = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdtcXJheHRudHRvcGtrZmxyaGxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzU0MDU3ODQsImV4cCI6MjA1MDk4MTc4NH0.GobJJmDBwEU6iu3iRaGIi8DEvTHy6cGu7gXRUm7uJnU")
        
        supabase = create_client(supabase_url, supabase_key)
        result = supabase.table("person_records").select("staff_id").limit(1).execute()
        
        logger.info("✅ Database connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.info("⚠️ Continuing anyway - will try to connect during runtime")
        return True  # Don't stop startup for DB issues

def start_server():
    """Start the FastAPI server"""
    try:
        import uvicorn
        from main import app
        
        port = int(os.getenv("PORT", 8000))
        host = os.getenv("HOST", "0.0.0.0")
        
        logger.info(f"🚀 Starting RelishAgro Backend on {host}:{port}")
        logger.info(f"🌍 Universal CORS enabled")
        logger.info(f"📱 All device compatibility: ✅")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)

def main():
    """Main startup function"""
    logger.info("🌱 RelishAgro Backend - Starting Up...")
    
    # Check environment
    if not check_environment():
        logger.error("❌ Environment check failed")
        sys.exit(1)
    
    # Check database
    check_database_connection()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()