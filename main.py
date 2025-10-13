from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="RelishAgro Backend API",
    description="Backend API for RelishAgro agricultural management system",
    version="1.0.0"
)

# CORS Configuration - FIXED WITH CORRECT DOMAIN
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:5173",  # Vite dev server
        "https://relishagro.vercel.app",  # ✅ CORRECT: Your actual frontend domain
        "https://relishagro-*.vercel.app",  # Pattern for preview deployments
        "https://*.vercel.app",  # Wildcard for Vercel domains
        "https://relishagrobackend-production.up.railway.app"  # Your backend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRFToken",
        "User-Agent",
        "Referer",
        "Origin"
    ],
)

# Security
security = HTTPBearer()

# Root endpoint
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "cors": "enabled",
        "frontend_url": "https://relishagro.vercel.app"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "cors_enabled": True
    }

# CORS test endpoint
@app.get("/api/cors-test")
async def cors_test():
    return {
        "message": "CORS is working!",
        "allowed_origins": [
            "https://relishagro.vercel.app",
            "http://localhost:3000"
        ]
    }

# Import and include routers with error handling and PROPER /api/ PREFIXES
try:
    from routes import auth
    app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
    print("✅ Auth routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import auth routes: {e}")

try:
    from routes import workers
    app.include_router(workers.router, prefix="/api/workers", tags=["workers"])
    print("✅ Workers routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import workers routes: {e}")

try:
    from routes import job_types
    app.include_router(job_types.router, prefix="/api/job-types", tags=["job-types"])
    print("✅ Job types routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import job_types routes: {e}")

try:
    from routes import provisions
    app.include_router(provisions.router, prefix="/api/provisions", tags=["provisions"])
    print("✅ Provisions routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import provisions routes: {e}")

try:
    from routes import onboarding
    app.include_router(onboarding.router, prefix="/api/onboarding", tags=["onboarding"])
    print("✅ Onboarding routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import onboarding routes: {e}")

try:
    from routes import attendance
    app.include_router(attendance.router, prefix="/api/attendance", tags=["attendance"])
    print("✅ Attendance routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import attendance routes: {e}")

try:
    from routes import gps_tracking  # FIXED: was 'gps' but file is 'gps_tracking.py'
    app.include_router(gps_tracking.router, prefix="/api/gps", tags=["gps-tracking"])
    print("✅ GPS tracking routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import gps_tracking routes: {e}")

try:
    from routes import face_recognition
    app.include_router(face_recognition.router, prefix="/api/face", tags=["face-recognition"])
    print("✅ Face recognition routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import face_recognition routes: {e}")

# CRITICAL: Include supervisor router with /api/supervisor prefix
try:
    from routes import supervisor
    app.include_router(supervisor.router, prefix="/api/supervisor", tags=["supervisor"])
    print("✅ Supervisor routes loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import supervisor routes: {e}")

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "status": "error",
        "message": exc.detail,
        "status_code": exc.status_code
    }

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        # Your existing token verification logic
        # For now, return a mock user - replace with actual auth logic
        return {"user_id": "1", "username": "admin"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Protected route example
@app.get("/api/protected")
async def protected_route(current_user: dict = Depends(verify_token)):
    return {
        "message": "This is a protected route",
        "user": current_user
    }

# Environment info (for debugging - remove in production)
@app.get("/api/env-info")
async def env_info():
    return {
        "database_url": "***" if os.getenv("DATABASE_URL") else "Not set",
        "supabase_url": "***" if os.getenv("SUPABASE_URL") else "Not set",
        "supabase_key": "***" if os.getenv("SUPABASE_KEY") else "Not set",
        "jwt_secret": "***" if os.getenv("JWT_SECRET") else "Not set",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True if os.getenv("ENVIRONMENT") != "production" else False
    )