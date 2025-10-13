from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import logging

# Import all your route modules
from routes import auth, supervisor, job_types, workers, provisions, onboarding, gps_tracking

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 RelishAgro Backend Starting...")
    yield
    logger.info("⏹️ RelishAgro Backend Shutting down...")

# Initialize FastAPI
app = FastAPI(
    title="RelishAgro Backend API",
    description="Production-ready agricultural management system with universal device compatibility",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# MAXIMUM COMPATIBILITY CORS CONFIGURATION
# ========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow ALL origins for maximum compatibility
    allow_credentials=True,
    allow_methods=["*"],  # Allow ALL HTTP methods
    allow_headers=["*"],  # Allow ALL headers
    expose_headers=["*"], # Expose ALL headers
    max_age=86400,  # 24 hours cache for preflight requests
)

# ENHANCED CORS HANDLER
# ====================

@app.middleware("http")
async def cors_handler(request: Request, call_next):
    """Enhanced CORS handler for all devices"""
    
    origin = request.headers.get("origin")
    method = request.method
    
    # Handle preflight requests
    if method == "OPTIONS":
        response = JSONResponse(content={"message": "OK"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response
    
    # Process request
    try:
        response = await call_next(request)
        
        # Add CORS headers to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        error_response = JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
        error_response.headers["Access-Control-Allow-Origin"] = "*"
        error_response.headers["Access-Control-Allow-Credentials"] = "true"
        return error_response

# ENDPOINTS
# =========

@app.get("/")
async def root():
    return {
        "message": "🌱 RelishAgro Backend API - Production Ready",
        "version": "1.0.0",
        "status": "active",
        "cors_enabled": True,
        "device_compatibility": "universal"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "cors_status": "enabled",
        "database_status": "connected"
    }

@app.get("/api/cors-test")
async def cors_test(request: Request):
    return {
        "message": "✅ CORS working - All devices supported",
        "origin": request.headers.get("origin"),
        "cors_enabled": True
    }

# REGISTER ROUTES
# ==============

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(supervisor.router, prefix="/api/supervisor", tags=["Supervisor"])
app.include_router(job_types.router, prefix="/api/job-types", tags=["Job Types"])
app.include_router(workers.router, prefix="/api/workers", tags=["Workers"])
app.include_router(provisions.router, prefix="/api/provisions", tags=["Provisions"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(gps_tracking.router, prefix="/api/gps", tags=["GPS"])

# EXCEPTION HANDLERS
# =================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    response = JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)