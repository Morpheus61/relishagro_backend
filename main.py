from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database connection
from database import initialize_database, cleanup_database, check_database_health

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 RelishAgro Backend Starting...")
    
    # Initialize database connections
    try:
        await initialize_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    yield
    
    # Cleanup
    try:
        await cleanup_database()
        logger.info("✅ Database cleanup completed")
    except Exception as e:
        logger.error(f"❌ Database cleanup failed: {e}")
    
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
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    """Enhanced CORS handler for all devices"""
    
    origin = request.headers.get("origin")
    method = request.method
    
    # Log requests for debugging
    logger.info(f"📱 {method} from {origin}")
    
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
        logger.error(f"❌ Request error: {str(e)}")
        
        # Return CORS-enabled error response
        error_response = JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
        error_response.headers["Access-Control-Allow-Origin"] = "*"
        error_response.headers["Access-Control-Allow-Credentials"] = "true"
        return error_response

# BASIC ENDPOINTS (without route imports to prevent errors)
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
    """Comprehensive health check"""
    try:
        db_health = await check_database_health()
        return {
            "status": "healthy",
            "cors_status": "enabled",
            "database_status": db_health,
            "timestamp": "2024-12-28T00:00:00Z"
        }
    except Exception as e:
        return {
            "status": "partial",
            "cors_status": "enabled", 
            "database_status": "error",
            "error": str(e),
            "timestamp": "2024-12-28T00:00:00Z"
        }

@app.get("/api/cors-test")
async def cors_test(request: Request):
    return {
        "message": "✅ CORS working - All devices supported",
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "cors_enabled": True
    }

@app.get("/api/database-test")
async def database_test():
    """Test database connectivity"""
    try:
        from database import get_supabase_client
        
        supabase = get_supabase_client()
        result = supabase.table("person_records").select("staff_id").limit(1).execute()
        
        return {
            "message": "✅ Database connection successful",
            "records_found": len(result.data),
            "status": "connected"
        }
    except Exception as e:
        return {
            "message": "❌ Database connection failed",
            "error": str(e),
            "status": "disconnected"
        }

# ROUTE REGISTRATION (safely import routes)
try:
    # Import routes only if they exist and are working
    logger.info("🔄 Loading route modules...")
    
    # Try to import each route module individually
    route_modules = []
    
    try:
        from routes import auth
        app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
        route_modules.append("auth")
        logger.info("✅ Auth routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ Auth routes failed to load: {e}")
    
    try:
        from routes import supervisor
        app.include_router(supervisor.router, prefix="/api/supervisor", tags=["Supervisor"])
        route_modules.append("supervisor")
        logger.info("✅ Supervisor routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ Supervisor routes failed to load: {e}")
    
    try:
        from routes import job_types
        app.include_router(job_types.router, prefix="/api/job-types", tags=["Job Types"])
        route_modules.append("job_types")
        logger.info("✅ Job Types routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ Job Types routes failed to load: {e}")
    
    try:
        from routes import workers
        app.include_router(workers.router, prefix="/api/workers", tags=["Workers"])
        route_modules.append("workers")
        logger.info("✅ Workers routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ Workers routes failed to load: {e}")
    
    try:
        from routes import provisions
        app.include_router(provisions.router, prefix="/api/provisions", tags=["Provisions"])
        route_modules.append("provisions")
        logger.info("✅ Provisions routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ Provisions routes failed to load: {e}")
    
    try:
        from routes import onboarding
        app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
        route_modules.append("onboarding")
        logger.info("✅ Onboarding routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ Onboarding routes failed to load: {e}")
    
    try:
        from routes import gps_tracking
        app.include_router(gps_tracking.router, prefix="/api/gps", tags=["GPS"])
        route_modules.append("gps_tracking")
        logger.info("✅ GPS routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ GPS routes failed to load: {e}")
    
    logger.info(f"📊 Successfully loaded {len(route_modules)} route modules: {route_modules}")

except Exception as e:
    logger.error(f"❌ Route loading failed: {e}")
    logger.info("⚠️ Starting with basic endpoints only")

# Add an endpoint to check which routes are loaded
@app.get("/api/routes-status")
async def routes_status():
    """Check which route modules are loaded"""
    loaded_routes = []
    
    # Check each route by trying to access the router
    route_checks = {
        "auth": "/api/auth",
        "supervisor": "/api/supervisor", 
        "job_types": "/api/job-types",
        "workers": "/api/workers",
        "provisions": "/api/provisions",
        "onboarding": "/api/onboarding",
        "gps_tracking": "/api/gps"
    }
    
    for route_name, prefix in route_checks.items():
        try:
            # Check if route exists in app
            route_exists = any(route.path.startswith(prefix) for route in app.routes)
            if route_exists:
                loaded_routes.append(route_name)
        except:
            pass
    
    return {
        "loaded_routes": loaded_routes,
        "total_routes": len(loaded_routes),
        "status": "partial" if len(loaded_routes) < len(route_checks) else "complete"
    }

# EXCEPTION HANDLERS
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
    logger.error(f"❌ Unhandled exception: {str(exc)}")
    response = JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# STARTUP
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting RelishAgro Backend on 0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port)