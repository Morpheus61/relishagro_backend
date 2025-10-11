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

# CORS Configuration — FIXED: Removed trailing spaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://relishagro.vercel.app",  # ✅ NO TRAILING SPACES
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

# Import routers with individual error handling
print("📦 Loading routers...")

# Auth router (critical - load first)
try:
    from config import settings
    from routes import auth_router
    app.include_router(auth_router, prefix=settings.API_PREFIX, tags=["Authentication"])
    print("✅ Auth router loaded")
except Exception as e:
    print(f"⚠️ Auth router error: {e}")

# Attendance router
try:
    from routes import attendance_router
    app.include_router(attendance_router, prefix=settings.API_PREFIX, tags=["Attendance"])
    print("✅ Attendance router loaded")
except Exception as e:
    print(f"⚠️ Attendance router error: {e}")

# Face Recognition router
try:
    from routes import face_router
    app.include_router(face_router, prefix=settings.API_PREFIX, tags=["Face Recognition"])
    print("✅ Face Recognition router loaded")
except Exception as e:
    print(f"⚠️ Face Recognition router error: {e}")

# Onboarding router
try:
    from routes import onboarding_router
    app.include_router(onboarding_router, prefix=settings.API_PREFIX, tags=["Onboarding"])
    print("✅ Onboarding router loaded")
except Exception as e:
    print(f"⚠️ Onboarding router error: {e}")

# Provisions router
try:
    from routes import provisions_router
    app.include_router(provisions_router, prefix=settings.API_PREFIX, tags=["Provisions"])
    print("✅ Provisions router loaded")
except Exception as e:
    print(f"⚠️ Provisions router error: {e}")

# GPS Tracking router
try:
    from routes import gps_router
    app.include_router(gps_router, prefix=settings.API_PREFIX, tags=["GPS Tracking"])
    print("✅ GPS Tracking router loaded")
except Exception as e:
    print(f"⚠️ GPS Tracking router error: {e}")

# Workers router
try:
    from routes import workers_router
    app.include_router(workers_router, prefix=settings.API_PREFIX, tags=["Workers"])
    print("✅ Workers router loaded")
except Exception as e:
    print(f"⚠️ Workers router error: {e}")

# Job Types router
try:
    from routes import job_types_router
    app.include_router(job_types_router, prefix=settings.API_PREFIX, tags=["Job Types"])
    print("✅ Job Types router loaded")
except Exception as e:
    print(f"⚠️ Job Types router error: {e}")

# Debug: Print all registered routes
print("🔍 Registered routes:")
for route in app.routes:
    if hasattr(route, 'methods'):
        print(f"  {route.methods} {route.path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=False)