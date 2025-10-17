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
        "https://relishagro.vercel.app",  # Production frontend
        "http://localhost:3000",         # Local development
        "http://localhost:5173",         # Vite dev server
        "http://127.0.0.1:3000",        # Alternative local
        "http://127.0.0.1:5173",        # Alternative Vite
        "https://localhost:3000",        # HTTPS local
        "https://127.0.0.1:3000",       # HTTPS alternative
        "*"  # Allow all origins for mobile browsers (be cautious in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=[
        "*",  # Allow all headers for mobile compatibility
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
        "X-CSRFToken",
        "X-Forwarded-For",
        "X-Real-IP"
    ],
    expose_headers=[
        "Content-Range",
        "X-Content-Range",
        "Accept-Ranges",
        "Content-Length",
        "Cache-Control",
        "Content-Language",
        "Content-Location",
        "Content-MD5",
        "Content-Range",
        "Content-Type",
        "Date",
        "ETag",
        "Expires",
        "Last-Modified",
        "Location",
        "Server"
    ]
)

# Add mobile-specific middleware
@app.middleware("http")
async def mobile_compatibility_middleware(request: Request, call_next):
    """
    Middleware to enhance mobile browser compatibility
    """
    # Log mobile requests for debugging
    user_agent = request.headers.get("user-agent", "")
    if any(mobile in user_agent.lower() for mobile in ['mobile', 'android', 'iphone', 'ipad']):
        logger.info(f"📱 Mobile request: {request.method} {request.url.path}")
        logger.info(f"📱 User-Agent: {user_agent}")
        logger.info(f"📱 Origin: {request.headers.get('origin', 'N/A')}")
    
    response = await call_next(request)
    
    # Add additional headers for mobile compatibility
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "86400"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Global exception: {str(exc)}")
    logger.error(f"📍 Request: {request.method} {request.url}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "mobile_debug": True
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_status = test_connection()
        return {
            "status": "healthy" if db_status else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected" if db_status else "disconnected",
            "version": "1.0.0",
            "mobile_compatible": True,
            "cors_enabled": True
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "mobile_compatible": True
            }
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "mobile_compatible": True,
        "docs": "/docs",
        "health": "/health"
    }

# Include all route modules - FIXED PREFIXES
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(workers.router, prefix="/api/workers", tags=["Workers"])  # ✅ FIXED
app.include_router(job_types.router, prefix="/api", tags=["Job Types"])  # Already correct
app.include_router(provisions.router, prefix="/api/provisions", tags=["Provisions"])  # ✅ FIXED
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])  # ✅ FIXED
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])  # ✅ FIXED
app.include_router(face_recognition.router, prefix="/api/face", tags=["Face Recognition"])  # ✅ FIXED
app.include_router(gps_tracking.router, prefix="/api/gps", tags=["GPS Tracking"])  # Already has /gps prefix
app.include_router(supervisor.router, prefix="/api/supervisor", tags=["Supervisor"])  # ✅ FIXED

# Startup message
@app.on_event("startup")
async def startup_event():
    logger.info("🎯 RelishAgro Backend API is ready!")
    logger.info("📱 Mobile compatibility: ENABLED")
    logger.info("🌐 CORS configuration: ENHANCED")
    logger.info("🔐 Authentication: Staff ID Only")
    logger.info("🚂 Railway deployment: OPTIMIZED")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,  # Railway uses port 8080
        reload=False,  # Disable reload in production
        log_level="info"
    )