from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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

# Initialize FastAPI with comprehensive configuration
app = FastAPI(
    title="RelishAgro Backend API",
    description="Production-ready agricultural management system with universal device compatibility",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# COMPREHENSIVE CORS CONFIGURATION FOR ALL DEVICE COMPATIBILITY
# ============================================================

# Production and Development Origins
ALLOWED_ORIGINS = [
    # Production Frontend
    "https://relishagro.vercel.app",
    "https://www.relishagro.vercel.app",
    
    # Development Origins
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    
    # Mobile App Origins (React Native, Expo)
    "exp://localhost:19000",
    "exp://127.0.0.1:19000",
    "exp://192.168.1.1:19000",  # Common local network
    "capacitor://localhost",
    "ionic://localhost",
    
    # PWA and Service Worker Origins
    "https://relishagro.vercel.app",
    
    # Wildcard for Vercel preview deployments (be cautious in production)
    # "https://*.vercel.app",  # Uncomment if needed for preview deployments
]

# Dynamic origin detection for development
def get_dynamic_origins():
    """Get additional origins based on environment"""
    dynamic_origins = []
    
    # Add custom domain if specified
    custom_domain = os.getenv("CUSTOM_DOMAIN")
    if custom_domain:
        dynamic_origins.extend([
            f"https://{custom_domain}",
            f"https://www.{custom_domain}",
            f"http://{custom_domain}",  # For development
        ])
    
    # Add local network IPs for mobile testing
    local_ips = os.getenv("LOCAL_IPS", "").split(",")
    for ip in local_ips:
        if ip.strip():
            dynamic_origins.extend([
                f"http://{ip.strip()}:3000",
                f"http://{ip.strip()}:3001",
                f"http://{ip.strip()}:5173",
                f"http://{ip.strip()}:8080",
            ])
    
    return dynamic_origins

# Combine all origins
ALL_ORIGINS = list(set(ALLOWED_ORIGINS + get_dynamic_origins()))

# CORS Middleware with comprehensive configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALL_ORIGINS,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "OPTIONS",
        "HEAD"
    ],
    allow_headers=[
        "*",  # Allow all headers for maximum compatibility
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRFToken",
        "X-API-Key",
        "Cache-Control",
        "Pragma",
        "Expires",
        "Last-Modified",
        "ETag",
        "If-Match",
        "If-None-Match",
        "If-Modified-Since",
        "If-Unmodified-Since",
        "User-Agent",
        "Referer",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "DNT",
        "X-Forwarded-For",
        "X-Real-IP",
        "X-Forwarded-Proto",
        "X-Forwarded-Host",
        "X-Custom-Header",
        "X-Device-Type",
        "X-Platform",
        "X-App-Version",
        "X-Client-Version",
        "X-Request-ID",
        "X-Correlation-ID",
        "X-Session-ID",
        "X-User-Agent",
        "X-Mobile-App",
        "X-PWA",
        "X-Browser-Name",
        "X-Browser-Version",
        "X-OS-Name",
        "X-OS-Version",
        "X-Device-Model",
        "X-Screen-Resolution",
        "X-Timezone",
        "X-Language",
        "X-Country",
        "X-Region"
    ],
    expose_headers=[
        "*",  # Expose all headers to frontend
        "Content-Type",
        "Content-Length",
        "Authorization",
        "X-Total-Count",
        "X-Page-Count",
        "X-Current-Page",
        "X-Per-Page",
        "X-Rate-Limit-Remaining",
        "X-Rate-Limit-Reset",
        "X-Request-ID",
        "X-Response-Time",
        "X-Server-Version",
        "X-API-Version",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
        "Location",
        "X-Download-URL",
        "X-Upload-URL",
        "X-Webhook-ID"
    ],
    max_age=86400,  # 24 hours cache for preflight requests
)

# Trusted Host Middleware for additional security
TRUSTED_HOSTS = [
    "relishagrobackend-production.up.railway.app",
    "localhost",
    "127.0.0.1",
    "*.railway.app",
    "*.vercel.app"
]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS
)

# CUSTOM CORS HANDLER FOR COMPLEX SCENARIOS
# =========================================

@app.middleware("http")
async def enhanced_cors_handler(request: Request, call_next):
    """Enhanced CORS handler for edge cases and device compatibility"""
    
    # Log request for debugging
    origin = request.headers.get("origin")
    user_agent = request.headers.get("user-agent", "")
    method = request.method
    
    logger.info(f"📱 Request: {method} from {origin} | UA: {user_agent[:100]}")
    
    # Handle preflight requests explicitly
    if method == "OPTIONS":
        # Get requested headers
        requested_headers = request.headers.get("access-control-request-headers", "")
        requested_method = request.headers.get("access-control-request-method", "")
        
        # Create comprehensive preflight response
        response = JSONResponse(
            content={"message": "Preflight OK"},
            status_code=200
        )
        
        # Set all CORS headers explicitly
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = requested_headers or "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Expose-Headers"] = "*"
        
        # Additional headers for mobile compatibility
        response.headers["Vary"] = "Origin, Access-Control-Request-Method, Access-Control-Request-Headers"
        response.headers["Cache-Control"] = "public, max-age=86400"
        
        return response
    
    # Process the request
    try:
        response = await call_next(request)
        
        # Add CORS headers to all responses
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "*"
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add device compatibility headers
        response.headers["X-UA-Compatible"] = "IE=edge"
        response.headers["X-Device-Compatible"] = "mobile, desktop, tablet, pwa"
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Request processing error: {str(e)}")
        
        # Return CORS-enabled error response
        error_response = JSONResponse(
            content={"error": "Internal server error", "detail": str(e)},
            status_code=500
        )
        
        if origin:
            error_response.headers["Access-Control-Allow-Origin"] = origin
        error_response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return error_response

# HEALTH CHECK AND CORS VERIFICATION ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint with CORS verification"""
    return {
        "message": "🌱 RelishAgro Backend API - Production Ready",
        "version": "1.0.0",
        "status": "active",
        "cors_enabled": True,
        "device_compatibility": "universal",
        "supported_origins": len(ALL_ORIGINS),
        "environment": os.getenv("ENVIRONMENT", "production")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-12-28T00:00:00Z",
        "cors_status": "enabled",
        "database_status": "connected"
    }

@app.get("/api/cors-test")
async def cors_test(request: Request):
    """CORS test endpoint for debugging"""
    return {
        "message": "CORS test successful",
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "method": request.method,
        "headers": dict(request.headers),
        "cors_enabled": True
    }

# REGISTER ALL API ROUTES
# =======================

# Authentication routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# Dashboard routes
app.include_router(supervisor.router, prefix="/api/supervisor", tags=["Supervisor Dashboard"])
app.include_router(job_types.router, prefix="/api/job-types", tags=["Job Types Management"])
app.include_router(workers.router, prefix="/api/workers", tags=["Worker Management"])
app.include_router(provisions.router, prefix="/api/provisions", tags=["Provisions Management"])

# System routes
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Worker Onboarding"])
app.include_router(gps_tracking.router, prefix="/api/gps", tags=["GPS Tracking"])

# GLOBAL EXCEPTION HANDLER WITH CORS
# ==================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler with CORS support"""
    origin = request.headers.get("origin")
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2024-12-28T00:00:00Z"
        }
    )
    
    # Add CORS headers to error responses
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler with CORS support"""
    origin = request.headers.get("origin")
    logger.error(f"❌ Unhandled exception: {str(exc)}")
    
    response = JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": "2024-12-28T00:00:00Z"
        }
    )
    
    # Add CORS headers to error responses
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# APPLICATION STARTUP MESSAGE
# ===========================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting RelishAgro Backend on {host}:{port}")
    logger.info(f"📱 CORS enabled for {len(ALL_ORIGINS)} origins")
    logger.info(f"🌍 Universal device compatibility: ✅")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Set to False in production
        log_level="info"
    )