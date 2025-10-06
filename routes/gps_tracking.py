from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from database import get_db
from models import Dispatch, GPSTrackingLog, GeofenceAlert, PersonRecord
from services import NotificationService
from utils import require_role
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import math

router = APIRouter(prefix="/gps", tags=["gps_tracking"])
notification_service = NotificationService()

class GPSLocation(BaseModel):
    latitude: float
    longitude: float
    speed: Optional[float] = None
    timestamp: str

class BatchGPSSync(BaseModel):
    dispatch_id: str
    locations: List[GPSLocation]

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates using Haversine formula"""
    R = 6371  # Earth radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

@router.post("/start-tracking/{dispatch_id}")
async def start_gps_tracking(
    dispatch_id: str,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["driver", "harvestflow_manager"]))
):
    """Start GPS tracking for a dispatch"""
    
    dispatch = db.query(Dispatch).filter(
        Dispatch.dispatch_id == uuid.UUID(dispatch_id)
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    dispatch.gps_tracking_active = True
    dispatch.trip_status = "in_transit"
    db.commit()
    
    return {
        "success": True,
        "message": "GPS tracking started",
        "dispatch_id": str(dispatch.dispatch_id)
    }

@router.post("/log-location")
async def log_gps_location(
    dispatch_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    speed: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["driver"]))
):
    """Log single GPS location (real-time)"""
    from config import settings
    
    dispatch = db.query(Dispatch).filter(
        Dispatch.dispatch_id == uuid.UUID(dispatch_id),
        Dispatch.driver_id == current_user.id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found or unauthorized")
    
    # Create GPS log
    gps_log = GPSTrackingLog(
        dispatch_id=dispatch.dispatch_id,
        latitude=latitude,
        longitude=longitude,
        speed=speed,
        timestamp=datetime.utcnow()
    )
    
    db.add(gps_log)
    
    # Check geofence
    # Distance from farm
    dist_from_farm = calculate_distance_km(
        latitude, longitude,
        settings.FARM_LATITUDE, settings.FARM_LONGITUDE
    )
    
    # Distance from processing unit
    dist_from_processing = calculate_distance_km(
        latitude, longitude,
        settings.PROCESSING_UNIT_LATITUDE, settings.PROCESSING_UNIT_LONGITUDE
    )
    
    # Alert if outside geofence
    if (dist_from_farm > settings.GPS_GEOFENCE_RADIUS_KM and 
        dist_from_processing > settings.GPS_GEOFENCE_RADIUS_KM):
        
        # Create alert
        alert = GeofenceAlert(
            dispatch_id=dispatch.dispatch_id,
            alert_type="route_deviation",
            latitude=latitude,
            longitude=longitude,
            message=f"Driver {current_user.full_name} outside geofence"
        )
        db.add(alert)
        
        # Notify managers
        managers = db.query(PersonRecord).filter(
            PersonRecord.person_type.in_(["harvestflow_manager", "flavorcore_manager", "admin"]),
            PersonRecord.status == "active"
        ).all()
        
        manager_ids = [m.id for m in managers]
        
        await notification_service.notify_geofence_alert(
            db=db,
            managers=manager_ids,
            driver_name=current_user.full_name,
            alert_type="Route Deviation"
        )
    
    db.commit()
    
    return {
        "success": True,
        "logged_at": gps_log.timestamp.isoformat(),
        "geofence_status": "inside" if (dist_from_farm <= settings.GPS_GEOFENCE_RADIUS_KM or 
                                        dist_from_processing <= settings.GPS_GEOFENCE_RADIUS_KM) else "outside"
    }

@router.post("/sync-batch")
async def sync_gps_batch(
    request: BatchGPSSync,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["driver"]))
):
    """Sync batch of offline GPS locations"""
    from utils import OfflineSyncQueue
    
    locations = [
        {
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "speed": loc.speed,
            "timestamp": loc.timestamp
        }
        for loc in request.locations
    ]
    
    result = await OfflineSyncQueue.sync_gps_batch(
        db=db,
        gps_records=locations,
        dispatch_id=uuid.UUID(request.dispatch_id)
    )
    
    return result

@router.get("/track/{dispatch_id}")
async def get_dispatch_tracking(
    dispatch_id: str,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["admin", "harvestflow_manager", "flavorcore_manager"]))
):
    """Get GPS tracking history for a dispatch"""
    
    logs = db.query(GPSTrackingLog).filter(
        GPSTrackingLog.dispatch_id == uuid.UUID(dispatch_id)
    ).order_by(GPSTrackingLog.timestamp.desc()).limit(100).all()
    
    return {
        "success": True,
        "count": len(logs),
        "locations": [
            {
                "latitude": float(log.latitude),
                "longitude": float(log.longitude),
                "speed": float(log.speed) if log.speed else None,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    }

@router.post("/complete/{dispatch_id}")
async def complete_dispatch(
    dispatch_id: str,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["driver"]))
):
    """Mark dispatch as delivered"""
    
    dispatch = db.query(Dispatch).filter(
        Dispatch.dispatch_id == uuid.UUID(dispatch_id),
        Dispatch.driver_id == current_user.id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    dispatch.trip_status = "delivered"
    dispatch.gps_tracking_active = False
    
    db.commit()
    
    return {
        "success": True,
        "message": "Dispatch marked as delivered"
    }