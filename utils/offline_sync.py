from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import AttendanceLog, GPSTrackingLog
from datetime import datetime
import uuid

class OfflineSyncQueue:
    """
    Handle offline data sync for attendance and GPS tracking.
    Data collected offline is queued and synced when connection restored.
    """
    
    @staticmethod
    async def sync_attendance_batch(
        db: Session,
        attendance_records: List[Dict[str, Any]],
        device_id: str
    ) -> Dict[str, Any]:
        """
        Sync batch of offline attendance records.
        """
        synced_count = 0
        failed_records = []
        
        for record in attendance_records:
            try:
                # Check for duplicates
                existing = db.query(AttendanceLog).filter(
                    AttendanceLog.person_id == uuid.UUID(record["person_id"]),
                    AttendanceLog.timestamp == datetime.fromisoformat(record["timestamp"]),
                    AttendanceLog.device_id == device_id
                ).first()
                
                if existing:
                    continue  # Skip duplicate
                
                # Create attendance record
                attendance = AttendanceLog(
                    person_id=uuid.UUID(record["person_id"]),
                    method=record["method"],
                    timestamp=datetime.fromisoformat(record["timestamp"]),
                    location=record.get("location", "main_gate"),
                    confidence_score=record.get("confidence_score"),
                    device_id=device_id,
                    synced_at=datetime.utcnow()
                )
                
                db.add(attendance)
                synced_count += 1
                
            except Exception as e:
                failed_records.append({
                    "record": record,
                    "error": str(e)
                })
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0
            }
        
        return {
            "success": True,
            "synced_count": synced_count,
            "failed_count": len(failed_records),
            "failed_records": failed_records
        }
    
    @staticmethod
    async def sync_gps_batch(
        db: Session,
        gps_records: List[Dict[str, Any]],
        dispatch_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Sync batch of offline GPS tracking records.
        """
        synced_count = 0
        
        for record in gps_records:
            try:
                gps_log = GPSTrackingLog(
                    dispatch_id=dispatch_id,
                    latitude=float(record["latitude"]),
                    longitude=float(record["longitude"]),
                    speed=record.get("speed"),
                    timestamp=datetime.fromisoformat(record["timestamp"]),
                    is_offline_queued=True,
                    synced_at=datetime.utcnow()
                )
                
                db.add(gps_log)
                synced_count += 1
                
            except Exception as e:
                print(f"❌ GPS sync error: {e}")
                continue
        
        try:
            db.commit()
            return {
                "success": True,
                "synced_count": synced_count
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }