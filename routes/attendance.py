from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import AttendanceLog, PersonRecord
from utils import require_role, OfflineSyncQueue
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import uuid

router = APIRouter(prefix="/attendance", tags=["attendance"])

class AttendanceLogRequest(BaseModel):
    person_id: str
    method: str
    location: str = "main_gate"
    confidence_score: Optional[float] = None
    device_id: Optional[str] = None

class BatchAttendanceSync(BaseModel):
    records: List[dict]
    device_id: str

@router.post("/log")
async def log_attendance(
    request: AttendanceLogRequest,
    db: Session = Depends(get_db)
):
    """
    Log attendance for a person.
    Used after face recognition or manual entry.
    """
    try:
        person = db.query(PersonRecord).filter(
            PersonRecord.id == uuid.UUID(request.person_id)
        ).first()
        
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Check for existing attendance today
        today = date.today()
        existing = db.query(AttendanceLog).filter(
            AttendanceLog.person_id == person.id,
            func.date(AttendanceLog.timestamp) == today
        ).first()
        
        if existing:
            return {
                "success": True,
                "message": "Already checked in today",
                "attendance_id": str(existing.id),
                "check_in_time": existing.timestamp.isoformat()
            }
        
        # Create attendance log
        attendance = AttendanceLog(
            person_id=person.id,
            method=request.method,
            location=request.location,
            confidence_score=request.confidence_score,
            device_id=request.device_id,
            timestamp=datetime.utcnow()
        )
        
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        
        return {
            "success": True,
            "message": "Attendance logged successfully",
            "attendance_id": str(attendance.id),
            "person": {
                "id": str(person.id),
                "name": person.full_name
            },
            "check_in_time": attendance.timestamp.isoformat(),
            "method": attendance.method
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-batch")
async def sync_attendance_batch(
    request: BatchAttendanceSync,
    db: Session = Depends(get_db)
):
    """
    Sync batch of offline attendance records.
    Used by tablets when connection is restored.
    """
    result = await OfflineSyncQueue.sync_attendance_batch(
        db=db,
        attendance_records=request.records,
        device_id=request.device_id
    )
    
    return result

@router.get("/records")
async def get_attendance_records(
    location: str = Query(...),
    date: str = Query(None),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["admin", "harvestflow_manager", "flavorcore_manager"]))
):
    """
    Get attendance records for a location and date.
    """
    from sqlalchemy import func
    
    query = db.query(AttendanceLog).join(PersonRecord)
    
    # Filter by location
    query = query.filter(AttendanceLog.location == location)
    
    # Filter by date if provided
    if date:
        target_date = datetime.fromisoformat(date).date()
        query = query.filter(func.date(AttendanceLog.timestamp) == target_date)
    else:
        # Default to today
        query = query.filter(func.date(AttendanceLog.timestamp) == date.today())
    
    query = query.order_by(AttendanceLog.timestamp.desc())
    
    records = query.all()
    
    return {
        "success": True,
        "count": len(records),
        "records": [
            {
                "id": str(record.id),
                "person_id": str(record.person_id),
                "person_name": record.person.full_name,
                "method": record.method,
                "timestamp": record.timestamp.isoformat(),
                "location": record.location,
                "confidence_score": float(record.confidence_score) if record.confidence_score else None,
                "status": record.status
            }
            for record in records
        ]
    }

@router.post("/checkout/{attendance_id}")
async def checkout(
    attendance_id: str,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["admin", "harvestflow_manager", "flavorcore_manager"]))
):
    """Mark checkout time for an attendance record"""
    attendance = db.query(AttendanceLog).filter(
        AttendanceLog.id == uuid.UUID(attendance_id)
    ).first()
    
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    attendance.check_out_time = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Checkout recorded",
        "check_out_time": attendance.check_out_time.isoformat()
    }