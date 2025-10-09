from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

# Lifespan
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

# Create app
app = FastAPI(
    title="RelishAgro Backend API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration - Use FastAPI's built-in CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://relishagro.vercel.app",
        "https://relishagro-frontend.vercel.app",  # In case you have multiple domains
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Local testing
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "https://relishagro.vercel.app",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Health endpoints
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "RelishAgro Backend API",
        "version": "1.0.0",
        "cors": "enabled"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "relishagro-backend",
        "version": "1.0.0",
        "timestamp": "2025-10-09"
    }

# Test CORS endpoint
@app.get("/test-cors")
async def test_cors():
    return {
        "message": "CORS is working correctly!",
        "timestamp": "2025-10-09",
        "backend_url": "Railway deployment active"
    }

# Import routers AFTER middleware setup
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
    
    # Include routers with API prefix
    app.include_router(auth_router, prefix=settings.API_PREFIX, tags=["Authentication"])
    app.include_router(attendance_router, prefix=settings.API_PREFIX, tags=["Attendance"])
    app.include_router(face_router, prefix=settings.API_PREFIX, tags=["Face Recognition"])
    app.include_router(onboarding_router, prefix=settings.API_PREFIX, tags=["Onboarding"])
    app.include_router(provisions_router, prefix=settings.API_PREFIX, tags=["Provisions"])
    app.include_router(gps_router, prefix=settings.API_PREFIX, tags=["GPS Tracking"])
    
    print("✅ All routers registered successfully")
except Exception as e:
    print(f"⚠️ Router error: {e}")

# Additional debugging endpoint
@app.get("/debug/cors")
async def debug_cors(request: Request):
    return {
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=True)