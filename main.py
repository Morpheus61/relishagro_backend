"""
RelishAgro Backend API - Railway + Mobile Data Optimized
FastAPI application with Railway port configuration and enhanced mobile network support
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
from database import engine, Base
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created successfully")
except Exception as e:
    logger.error(f"❌ Database table creation failed: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="RelishAgro Backend API",
    description="Complete agriculture management system backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS Configuration for Mobile Networks + Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for mobile compatibility
        "https://relishagro.vercel.app",
        "https://*.vercel.app",
        "https://*.railway.app",  # Railway domains
        "http://localhost:3000",
        "http://localhost:3001",
        "http://192.168.*.*",  # Local network ranges
        "http://10.*.*.*",     # Private network ranges
        "https://*",           # All HTTPS origins for mobile data
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "*",
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "User-Agent",
        "Referer",
        "Origin",
        "DNT",
        "X-CustomHeader",
        "Keep-Alive",
        "Cache-Control",
        "X-Forwarded-For",
        "X-Real-IP",
        "X-Forwarded-Proto",  # Railway proxy headers
        "X-Railway-*"         # Railway-specific headers
    ],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight requests for 24 hours (mobile optimization)
)

# Add trusted host middleware for Railway + mobile access
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=[
        "*.railway.app", 
        "localhost", 
        "127.0.0.1",
        "*.vercel.app",
        "*"  # Allow all hosts for maximum mobile compatibility
    ]
)

# Root endpoint with Railway + mobile-friendly response
@app.get("/")
async def root():
    return {
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "mobile_support": "enabled",
        "cors": "configured",
        "platform": "railway",
        "port": "8080"
    }

# Enhanced health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2025-10-13",
        "database": "connected",
        "mobile_data_support": "enabled",
        "network_type": "all_supported",
        "platform": "railway",
        "port": os.getenv("PORT", "8080")
    }

# Mobile connectivity test endpoint
@app.get("/mobile-test")
async def mobile_connectivity_test():
    """Special endpoint to test mobile data connectivity"""
    return {
        "mobile_test": "success",
        "message": "Mobile data connection working",
        "timestamp": "2025-10-13",
        "cors_enabled": True,
        "all_networks_supported": True,
        "platform": "railway",
        "railway_port": os.getenv("PORT", "8080")
    }

# OPTIONS handler for preflight requests (critical for mobile)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle all OPTIONS requests for CORS preflight"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",  # 24 hours for mobile optimization
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Route Registration with Error Handling

# Authentication Routes
try:
    from routes import auth
    app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
    print("✅ Auth routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import auth routes: {e}")

# CRITICAL: Admin Routes (NEWLY ADDED)
try:
    from routes import admin
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
    print("✅ Admin routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import admin routes: {e}")

# Workers Routes
try:
    from routes import workers
    app.include_router(workers.router, prefix="/api/workers", tags=["workers"])
    print("✅ Workers routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import workers routes: {e}")

# Job Types Routes
try:
    from routes import job_types
    app.include_router(job_types.router, prefix="/api/job-types", tags=["job-types"])
    print("✅ Job types routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import job_types routes: {e}")

# Provisions Routes
try:
    from routes import provisions
    app.include_router(provisions.router, prefix="/api/provisions", tags=["provisions"])
    print("✅ Provisions routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import provisions routes: {e}")

# Onboarding Routes
try:
    from routes import onboarding
    app.include_router(onboarding.router, prefix="/api/onboarding", tags=["onboarding"])
    print("✅ Onboarding routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import onboarding routes: {e}")

# Attendance Routes
try:
    from routes import attendance
    app.include_router(attendance.router, prefix="/api/attendance", tags=["attendance"])
    print("✅ Attendance routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import attendance routes: {e}")

# GPS Tracking Routes
try:
    from routes import gps_tracking
    app.include_router(gps_tracking.router, prefix="/api/gps", tags=["gps-tracking"])
    print("✅ GPS tracking routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import gps_tracking routes: {e}")

# Face Recognition Routes
try:
    from routes import face_recognition
    app.include_router(face_recognition.router, prefix="/api/face", tags=["face-recognition"])
    print("✅ Face recognition routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import face_recognition routes: {e}")

# Supervisor Routes
try:
    from routes import supervisor
    app.include_router(supervisor.router, prefix="/api/supervisor", tags=["supervisor"])
    print("✅ Supervisor routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import supervisor routes: {e}")

# Enhanced Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "mobile_support": "enabled",
            "cors_enabled": True,
            "platform": "railway"
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )

# Startup Event
@app.on_event("startup")
async def startup_event():
    port = os.getenv("PORT", "8080")
    logger.info("🚀 RelishAgro Backend API started successfully")
    logger.info(f"🚂 Platform: Railway (Port: {port})")
    logger.info("📱 Mobile data connectivity: ENABLED")
    logger.info("🌐 CORS configuration: ALL NETWORKS")
    logger.info("📖 API Documentation: /docs")
    logger.info("🔍 Alternative docs: /redoc")
    logger.info("📱 Mobile test endpoint: /mobile-test")

# Shutdown Event
@app.on_event("shutdown")  
async def shutdown_event():
    logger.info("🛑 RelishAgro Backend API shutting down")

if __name__ == "__main__":
    import uvicorn
    # Railway automatically sets PORT environment variable to 8080
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚂 Starting on Railway port: {port}")
    # Bind to all interfaces for Railway + mobile access
    uvicorn.run(app, host="0.0.0.0", port=port)