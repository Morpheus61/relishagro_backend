from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
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

# CRITICAL: Add middleware BEFORE any routes or imports
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    print(f"🔍 CORS Middleware triggered: {request.method} {request.url.path}")  # Debug log
    
    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        print("✅ Handling OPTIONS preflight")
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",  # Changed to wildcard for testing
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",  # Allow all headers
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600",
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add CORS headers to response
    response.headers["Access-Control-Allow-Origin"] = "*"  # Wildcard for testing
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    print(f"✅ CORS headers added to response")
    return response

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Health endpoints - Add BEFORE router imports
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "RelishAgro Backend API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "relishagro-backend",
        "version": "1.0.0"
    }

# Test CORS endpoint
@app.get("/test-cors")
async def test_cors():
    return {"message": "If you can see this, CORS is working!", "timestamp": "2025-10-09"}

# Import routers AFTER middleware and base routes
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
    
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(attendance_router, prefix=settings.API_PREFIX)
    app.include_router(face_router, prefix=settings.API_PREFIX)
    app.include_router(onboarding_router, prefix=settings.API_PREFIX)
    app.include_router(provisions_router, prefix=settings.API_PREFIX)
    app.include_router(gps_router, prefix=settings.API_PREFIX)
    
    print("✅ All routers registered successfully")
except Exception as e:
    print(f"⚠️ Router error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))