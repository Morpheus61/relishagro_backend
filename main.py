from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import all your existing routes
from routes import auth, workers, job_types, provisions, onboarding, gps
from routes import supervisor  # NEW: Import supervisor routes

# Import your existing core modules
from core.database import init_db
from core.auth import get_current_user

# Lifespan manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

# Create FastAPI app with lifespan
app = FastAPI(
    title="RelishAgro Backend API",
    description="Backend API for RelishAgro agricultural management system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://relishagro-frontend.vercel.app",
        "https://relishagro-frontend-git-main-yourproject.vercel.app",
        "https://relishagro-frontend-yourproject.vercel.app",
        "https://*.vercel.app",
        "https://relishagrobackend-production.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
        "cors": "enabled"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }

# Include all existing routers
app.include_router(auth.router)
app.include_router(workers.router)
app.include_router(job_types.router)
app.include_router(provisions.router)
app.include_router(onboarding.router)
app.include_router(gps.router)

# NEW: Include supervisor router
app.include_router(supervisor.router)

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        # Your existing token verification logic
        return await get_current_user(credentials.credentials)
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
