from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os

# Custom CORS middleware for preflight
class CORSHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight
        if request.method == "OPTIONS":
            return Response(
                content="",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin or "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "3600",
                }
            )
        
        # Handle actual request
        response = await call_next(request)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

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
    print("👋 Shutting down...")

# Create app
app = FastAPI(
    title="RelishAgro Backend API",
    version="1.0.0",
    lifespan=lifespan
)

# Add custom CORS middleware FIRST
app.add_middleware(CORSHeadersMiddleware)

# Then add FastAPI CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This will be overridden by custom middleware
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)}
    )

# Health endpoints
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

# Import routers
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
except Exception as e:
    print(f"⚠️ Router error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))