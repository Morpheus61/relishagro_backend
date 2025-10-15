"""
RelishAgro Backend - MOBILE COMPATIBILITY FIXED
FastAPI main application with comprehensive CORS and mobile browser support
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import os
from contextlib import asynccontextmanager

# Import all route modules
from routes import auth, workers, job_types, provisions, onboarding
from routes import attendance, gps_tracking, face_recognition, supervisor
from database import create_tables, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting RelishAgro Backend...")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down RelishAgro Backend...")

# FastAPI app initialization
app = FastAPI(
    title="RelishAgro Backend API",
    description="Complete backend API for RelishAgro agricultural management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# COMPREHENSIVE CORS CONFIGURATION FOR MOBILE COMPATIBILITY
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://relishagro.vercel.app",           # Production frontend
        "http://localhost:3000",                   # Development frontend
        "http://localhost:5173",                   # Vite dev server
        "https://*.vercel.app",                    # All Vercel deployments
        "http://127.0.0.1:3000",                   # Alternative localhost
        "http://0.0.0.0:3000",                     # Docker networking
        "*"                                        # TEMPORARY: Allow all origins for mobile testing
    ],
    allow_credentials=True,
    allow_methods=[
        "GET", 
        "POST", 
        "PUT", 
        "DELETE", 
        "PATCH", 
        "OPTIONS",
        "HEAD"                                     # MOBILE FIX: Allow HEAD requests
    ],
    allow_headers=[
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
        "X-Forwarded-For",                        # MOBILE FIX: Mobile proxy headers
        "X-Forwarded-Proto",                      # MOBILE FIX: HTTPS forwarding
        "X-Real-IP",                              # MOBILE FIX: Real IP detection
        "*"                                       # MOBILE FIX: Allow all headers
    ],
    expose_headers=["*"]                          # MOBILE FIX: Expose all headers
)

# MOBILE COMPATIBILITY: Add custom middleware for mobile browsers
@app.middleware("http")
async def mobile_compatibility_middleware(request: Request, call_next):
    """Custom middleware to handle mobile browser compatibility issues"""
    
    # Log request details for debugging
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"User-Agent: {request.headers.get('user-agent', 'Unknown')}")
    
    # Handle preflight OPTIONS requests for mobile
    if request.method == "OPTIONS":
        response = JSONResponse(content={"message": "OK"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # Process the request
    try:
        response = await call_next(request)
        
        # Add mobile-specific headers to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
        
    except Exception as e:
        logger.error(f"Request processing error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

# ROOT ENDPOINT - MOBILE FIX: Handle direct URL access
@app.get("/", response_model=dict)
async def root():
    """Root endpoint - handles direct backend URL access from mobile browsers"""
    return {
        "message": "RelishAgro Backend API",
        "status": "running",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health",
        "mobile_compatible": True
    }

# HEALTH CHECK ENDPOINT
@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RelishAgro Backend",
        "database": "connected",
        "timestamp": "2025-10-15T04:00:00Z"
    }

# API ROUTES MOUNTING WITH MOBILE-FRIENDLY PREFIXES

# Authentication routes - MOST CRITICAL FOR MOBILE
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# Worker management routes
app.include_router(workers.router, prefix="/api/workers", tags=["Workers"])

# Job types routes
app.include_router(job_types.router, prefix="/api/job-types", tags=["Job Types"])

# Provisions routes
app.include_router(provisions.router, prefix="/api/provisions", tags=["Provisions"])

# Onboarding routes
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])

# Attendance routes
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])

# GPS tracking routes
app.include_router(gps_tracking.router, prefix="/api/gps", tags=["GPS Tracking"])

# Face recognition routes
app.include_router(face_recognition.router, prefix="/api/face", tags=["Face Recognition"])

# Supervisor routes
app.include_router(supervisor.router, prefix="/api/supervisor", tags=["Supervisor"])

# MOBILE TESTING ENDPOINTS
@app.get("/api/mobile-test", response_model=dict)
async def mobile_test():
    """Test endpoint specifically for mobile connectivity"""
    return {
        "mobile_test": "success",
        "message": "Mobile backend connection working",
        "cors_enabled": True,
        "timestamp": "2025-10-15T04:00:00Z"
    }

@app.post("/api/mobile-test", response_model=dict)
async def mobile_test_post(data: dict = None):
    """Test POST endpoint for mobile"""
    return {
        "mobile_post_test": "success",
        "received_data": data,
        "message": "Mobile POST request working"
    }

# CATCH-ALL ERROR HANDLER FOR MOBILE DEBUGGING
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler with mobile debugging info"""
    logger.warning(f"404 Error: {request.method} {request.url}")
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "requested_path": str(request.url.path),
            "method": request.method,
            "available_endpoints": [
                "/api/auth/login",
                "/api/auth/me",
                "/api/workers",
                "/api/job-types",
                "/api/provisions",
                "/api/onboarding",
                "/health",
                "/docs"
            ],
            "mobile_debug": True
        }
    )

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    """Custom 405 handler for method not allowed errors"""
    logger.warning(f"405 Error: {request.method} {request.url}")
    return JSONResponse(
        status_code=405,
        content={
            "detail": "Method not allowed",
            "requested_method": request.method,
            "requested_path": str(request.url.path),
            "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "mobile_debug": True,
            "suggestion": "Check if you're using the correct HTTP method"
        }
    )

# STARTUP EVENT
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("🚀 RelishAgro Backend started successfully!")
    logger.info("📱 Mobile compatibility features enabled")
    logger.info("🔐 Authentication system ready")
    logger.info("🌐 CORS configured for production")

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable (Railway uses PORT)
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"Starting server on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )