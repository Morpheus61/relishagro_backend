from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting RelishAgro Backend...")
    try:
        from database import engine, Base
        Base.metadata.create_all(bind=engine)
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database warning: {e}")
    yield
    print("👋 Shutting down...")

# Create app
app = FastAPI(
    title="RelishAgro Backend API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "https://relishagro.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)}
    )

# Health endpoints - MUST come before router imports
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "health": "/health"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "relishagro-backend",
        "version": "1.0.0"
    }

# Now import and register routers
print("📦 Loading routers...")
try:
    from config import settings
    from routes import (
        auth_router,
        attendance_router,
        face_router,
        onboarding_router,
        provisions_router,
        gps_router
    )
    
    app.include_router(auth_router, prefix=settings.API_PREFIX, tags=["auth"])
    app.include_router(attendance_router, prefix=settings.API_PREFIX, tags=["attendance"])
    app.include_router(face_router, prefix=settings.API_PREFIX, tags=["face"])
    app.include_router(onboarding_router, prefix=settings.API_PREFIX, tags=["onboarding"])
    app.include_router(provisions_router, prefix=settings.API_PREFIX, tags=["provisions"])
    app.include_router(gps_router, prefix=settings.API_PREFIX, tags=["gps"])
    
    print("✅ All routers registered successfully")
except ImportError as e:
    print(f"⚠️ Router import warning: {e}")
except Exception as e:
    print(f"❌ Router registration error: {e}")

# This won't be used by Railway (uses railway.json startCommand)
# But useful for local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),  # Use 8080 as default
        reload=True
    )