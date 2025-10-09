from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

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

app = FastAPI(
    title="RelishAgro Backend API",
    version="1.0.0",
    lifespan=lifespan
)

# CORRECT PRODUCTION CORS — NO TRAILING SPACES
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://relishagro.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)}
    )

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
        "version": "1.0.0"
    }

# Import routers AFTER middleware
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
    
    app.include_router(auth_router, prefix=settings.API_PREFIX, tags=["Authentication"])
    app.include_router(attendance_router, prefix=settings.API_PREFIX, tags=["Attendance"])
    app.include_router(face_router, prefix=settings.API_PREFIX, tags=["Face Recognition"])
    app.include_router(onboarding_router, prefix=settings.API_PREFIX, tags=["Onboarding"])
    app.include_router(provisions_router, prefix=settings.API_PREFIX, tags=["Provisions"])
    app.include_router(gps_router, prefix=settings.API_PREFIX, tags=["GPS Tracking"])
    
    print("✅ All routers registered successfully")
except Exception as e:
    print(f"⚠️ Router error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=False)