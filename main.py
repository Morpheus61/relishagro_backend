"""
RelishAgro Backend - CORRECTED Mobile-Compatible Main Application
This file is corrected to work with the ACTUAL database.py structure
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RelishAgro Backend API",
    description="Backend API for RelishAgro agricultural management system - Mobile Compatible",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ✅ CORRECTED CORS: Wildcard for mobile data compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Allow all origins for mobile data
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours (mobile optimization)
)

# ✅ OPTIONS handler for preflight requests (critical for mobile)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle all OPTIONS requests for CORS preflight"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# ROOT ENDPOINT
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "mobile_compatible": True,
        "cors": "enabled",
        "frontend_url": "https://relishagro.vercel.app",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs"
    }

# HEALTH CHECK ENDPOINT
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mobile_compatible": True,
        "cors_enabled": True
    }

# MOBILE TEST ENDPOINT
@app.get("/mobile-test")
async def mobile_test():
    """Test endpoint for mobile connectivity"""
    return {
        "mobile_test": "success",
        "message": "Mobile backend connection working",
        "cors_enabled": True,
        "timestamp": datetime.utcnow().isoformat()
    }

# Route Registration with Error Handling
try:
    from routes import auth
    app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
    logger.info("✅ Auth routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import auth routes: {e}")

try:
    from routes import workers
    app.include_router(workers.router, prefix="/api/workers", tags=["workers"])
    logger.info("✅ Workers routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import workers routes: {e}")

try:
    from routes import job_types
    app.include_router(job_types.router, prefix="/api/job-types", tags=["job-types"])
    logger.info("✅ Job types routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import job_types routes: {e}")

try:
    from routes import provisions
    app.include_router(provisions.router, prefix="/api/provisions", tags=["provisions"])
    logger.info("✅ Provisions routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import provisions routes: {e}")

try:
    from routes import onboarding
    app.include_router(onboarding.router, prefix="/api/onboarding", tags=["onboarding"])
    logger.info("✅ Onboarding routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import onboarding routes: {e}")

try:
    from routes import attendance
    app.include_router(attendance.router, prefix="/api/attendance", tags=["attendance"])
    logger.info("✅ Attendance routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import attendance routes: {e}")

try:
    from routes import gps_tracking
    app.include_router(gps_tracking.router, prefix="/api/gps", tags=["gps-tracking"])
    logger.info("✅ GPS tracking routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import gps_tracking routes: {e}")

try:
    from routes import face_recognition
    app.include_router(face_recognition.router, prefix="/api/face", tags=["face-recognition"])
    logger.info("✅ Face recognition routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import face_recognition routes: {e}")

try:
    from routes import supervisor
    app.include_router(supervisor.router, prefix="/api/supervisor", tags=["supervisor"])
    logger.info("✅ Supervisor routes loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Could not import supervisor routes: {e}")

# Custom error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler"""
    logger.warning(f"404 Error: {request.method} {request.url}")
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "requested_path": str(request.url.path),
            "method": request.method,
            "mobile_debug": True
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "mobile_compatible": True
        }
    )

# STARTUP EVENT
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("🚀 RelishAgro Backend started successfully!")
    logger.info("📱 Mobile compatibility features enabled")
    logger.info("🌐 CORS configured for all networks")
    logger.info("📖 API Documentation: /docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("🛑 RelishAgro Backend shutting down...")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚂 Starting on Railway port: {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )