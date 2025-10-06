from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import engine, Base
from routes import (
    auth_router,
    attendance_router,
    face_router,
    onboarding_router,
    provisions_router,
    gps_router
)
from config import settings
import uvicorn

# Create database tables
# Database initialization - moved to startup event to avoid blocking
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create tables: {e}")
    yield
    # Shutdown: cleanup if needed

app = FastAPI(
    title="RelishAgro Backend API",
    description="Production-ready backend for HarvestFlow and FlavorCore management",
    version="1.0.0",
    lifespan=lifespan  # Add this
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "detail": "Internal server error"
        }
    )

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "relishagro-backend",
        "version": "1.0.0"
    }

# Include routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(attendance_router, prefix=settings.API_PREFIX)
app.include_router(face_router, prefix=settings.API_PREFIX)
app.include_router(onboarding_router, prefix=settings.API_PREFIX)
app.include_router(provisions_router, prefix=settings.API_PREFIX)
app.include_router(gps_router, prefix=settings.API_PREFIX)

# Additional routes for remaining functionality
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Lot, FlavorCoreProcessing, QRLabel, RFIDTag, WorkTiming, DailyJobType, PersonRecord
from utils import require_role
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime, date

# Lots management router
lots_router = APIRouter(prefix=f"{settings.API_PREFIX}/lots", tags=["lots"])

class LotCreation(BaseModel):
    crop: str
    date_harvested: str
    raw_weight: Optional[float] = None
    half_day_weight: Optional[float] = None
    full_day_weight: Optional[float] = None
    threshed_weight: Optional[float] = None
    workers_involved: Optional[List[str]] = None

@lots_router.post("/create")
async def create_lot(
    lot_data: LotCreation,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["harvestflow_manager"]))
):
    """HarvestFlow Manager creates new lot"""
    
    # Generate lot_id: LOT-YYYY-NNN
    year = datetime.now().year
    count = db.query(Lot).filter(
        Lot.lot_id.like(f"LOT-{year}-%")
    ).count()
    
    lot_id = f"LOT-{year}-{count + 1:03d}"
    
    # Calculate yield if weights available
    estate_yield = None
    if lot_data.full_day_weight and lot_data.threshed_weight:
        estate_yield = (lot_data.threshed_weight / lot_data.full_day_weight) * 100
    
    lot = Lot(
        lot_id=lot_id,
        crop=lot_data.crop,
        date_harvested=datetime.fromisoformat(lot_data.date_harvested).date(),
        raw_weight=lot_data.raw_weight,
        half_day_weight=lot_data.half_day_weight,
        full_day_weight=lot_data.full_day_weight,
        threshed_weight=lot_data.threshed_weight,
        estate_yield_pct=estate_yield,
        workers_involved=[uuid.UUID(w) for w in lot_data.workers_involved] if lot_data.workers_involved else None,
        created_by=current_user.id
    )
    
    db.add(lot)
    db.commit()
    db.refresh(lot)
    
    return {
        "success": True,
        "lot_id": lot.lot_id,
        "estate_yield_pct": float(estate_yield) if estate_yield else None
    }

@lots_router.get("/list")
async def list_lots(
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["harvestflow_manager", "flavorcore_manager", "flavorcore_supervisor", "admin"]))
):
    """List all lots"""
    lots = db.query(Lot).order_by(Lot.date_harvested.desc()).limit(100).all()
    
    return {
        "success": True,
        "count": len(lots),
        "lots": [
            {
                "lot_id": lot.lot_id,
                "crop": lot.crop,
                "date_harvested": lot.date_harvested.isoformat(),
                "threshed_weight": float(lot.threshed_weight) if lot.threshed_weight else None,
                "estate_yield_pct": float(lot.estate_yield_pct) if lot.estate_yield_pct else None
            }
            for lot in lots
        ]
    }

# FlavorCore processing router
processing_router = APIRouter(prefix=f"{settings.API_PREFIX}/processing", tags=["processing"])

@processing_router.post("/rfid-scan")
async def rfid_in_scan(
    lot_id: str,
    verified_weight: float,
    rfid_tags: List[str],
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["flavorcore_supervisor"]))
):
    """FlavorCore Supervisor performs RFID in-scan"""
    
    lot = db.query(Lot).filter(Lot.lot_id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    
    process = FlavorCoreProcessing(
        lot_id=lot_id,
        in_scan_weight=verified_weight,
        in_scan_date=datetime.utcnow(),
        supervisor_id=current_user.id,
        status="in_progress"
    )
    
    db.add(process)
    db.commit()
    db.refresh(process)
    
    return {
        "success": True,
        "process_id": str(process.process_id),
        "lot_data": {
            "lot_id": lot.lot_id,
            "crop": lot.crop,
            "harvest_date": lot.date_harvested.isoformat(),
            "estate_weight": float(lot.threshed_weight) if lot.threshed_weight else None
        }
    }

@processing_router.post("/log-sample")
async def log_drying_sample(
    process_id: str,
    product_type: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["flavorcore_supervisor"]))
):
    """Log drying sample test"""
    
    process = db.query(FlavorCoreProcessing).filter(
        FlavorCoreProcessing.process_id == uuid.UUID(process_id)
    ).first()
    
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    sample = {
        "timestamp": datetime.utcnow().isoformat(),
        "product_type": product_type,
        "notes": notes
    }
    
    if process.sample_tests:
        process.sample_tests.append(sample)
    else:
        process.sample_tests = [sample]
    
    db.commit()
    
    return {"success": True, "sample_logged": True}

@processing_router.post("/generate-qr")
async def generate_qr_label(
    process_id: str,
    product_type: str,
    net_weight: float,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["flavorcore_supervisor"]))
):
    """Generate QR label with full traceability"""
    
    process = db.query(FlavorCoreProcessing).filter(
        FlavorCoreProcessing.process_id == uuid.UUID(process_id)
    ).first()
    
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    lot = db.query(Lot).filter(Lot.lot_id == process.lot_id).first()
    
    # Generate unique QR code
    qr_code = f"QR-{process.lot_id}-{uuid.uuid4().hex[:8].upper()}"
    
    # Build traceability data
    traceability = {
        "product_type": product_type,
        "net_weight_kg": net_weight,
        "harvest_date": lot.date_harvested.isoformat(),
        "lot_id": lot.lot_id,
        "crop": lot.crop,
        "processing_date": process.in_scan_date.isoformat() if process.in_scan_date else None,
        "supervisor": current_user.full_name,
        "farm_location": "Relish Agro, Maramalai, Kanyakumari District, PIN: 629851",
        "generated_at": datetime.utcnow().isoformat()
    }
    
    qr_label = QRLabel(
        qr_code=qr_code,
        process_id=process.process_id,
        product_type=product_type,
        net_weight=net_weight,
        traceability_data=traceability,
        generated_by=current_user.id
    )
    
    db.add(qr_label)
    db.commit()
    
    return {
        "success": True,
        "qr_code": qr_code,
        "traceability_data": traceability
    }

@processing_router.post("/submit-completion/{process_id}")
async def submit_lot_completion(
    process_id: str,
    final_products: List[dict],
    by_products: List[dict],
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["flavorcore_supervisor"]))
):
    """Submit completed lot for FC Manager approval"""
    from services import NotificationService
    
    process = db.query(FlavorCoreProcessing).filter(
        FlavorCoreProcessing.process_id == uuid.UUID(process_id)
    ).first()
    
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    process.final_products = final_products
    process.by_products = by_products
    process.status = "awaiting_approval"
    process.submitted_at = datetime.utcnow()
    
    # Calculate yields
    total_product = sum(p.get("weight", 0) for p in final_products)
    if process.in_scan_weight:
        process.flavorcore_yield_pct = (total_product / process.in_scan_weight) * 100
    
    db.commit()
    
    # Notify FC Manager
    notification_service = NotificationService()
    fc_managers = db.query(PersonRecord).filter(
        PersonRecord.person_type == "flavorcore_manager",
        PersonRecord.status == "active"
    ).all()
    
    for manager in fc_managers:
        await notification_service.notify_lot_completion(
            db=db,
            manager_id=manager.id,
            lot_id=process.lot_id,
            supervisor_name=current_user.full_name
        )
    
    return {
        "success": True,
        "message": "Lot completion submitted for approval"
    }

app.include_router(lots_router)
app.include_router(processing_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )