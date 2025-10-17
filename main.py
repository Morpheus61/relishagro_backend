"""
RelishAgro Backend - Main Application (MOBILE CORS COMPLETE)
Enhanced CORS configuration for mobile browser compatibility
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import uvicorn
from datetime import datetime

# Import database and routes
from database import init_db, test_connection
from routes import auth, admin, workers, job_types, provisions, onboarding, attendance, face_recognition, gps_tracking, supervisor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 RelishAgro Backend Starting...")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database...")
        init_db()
        
        # Test database connection
        logger.info("🔍 Testing database connection...")
        if test_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.error("❌ Database connection failed")
            
        logger.info("✅ Backend startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}")
        raise e
    
    yield
    
    # Shutdown
    logger.info("🛑 RelishAgro Backend Shutting Down...")

# Create FastAPI app
app = FastAPI(
    title="RelishAgro Backend API",
    description="Complete RelishAgro management system with mobile compatibility",
    version="1.0.0",
    lifespan=lifespan
)

# ENHANCED CORS Configuration for Mobile Compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://relishagro.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://localhost:3000",
        "https://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add mobile-specific middleware
@app.middleware("http")
async def mobile_compatibility_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    db_status = test_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_status else "disconnected",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

# ✅ CORRECT ROUTER REGISTRATION - BACK TO ORIGINAL WORKING CONFIG
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(workers.router, prefix="/api/workers", tags=["Workers"])
app.include_router(job_types.router, prefix="/api", tags=["Job Types"])
app.include_router(provisions.router, prefix="/api/provisions", tags=["Provisions"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(attendance.router, prefix="/api", tags=["Attendance"])
app.include_router(face_recognition.router, prefix="/api", tags=["Face Recognition"])
app.include_router(gps_tracking.router, prefix="/api", tags=["GPS Tracking"])
app.include_router(supervisor.router, prefix="/api", tags=["Supervisor"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )