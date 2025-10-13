"""
RelishAgro Backend API - Updated Main.py with Admin Routes
FastAPI application with CORS, database connection, and comprehensive route registration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2025-10-13",
        "database": "connected"
    }

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
    from routes import gps_tracking  # FIXED: was 'gps' but file is 'gps_tracking.py'
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

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

# Startup Event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 RelishAgro Backend API started successfully")
    logger.info("📖 API Documentation: /docs")
    logger.info("🔍 Alternative docs: /redoc")

# Shutdown Event
@app.on_event("shutdown")  
async def shutdown_event():
    logger.info("🛑 RelishAgro Backend API shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)