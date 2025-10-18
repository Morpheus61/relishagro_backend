# routes/attendance.py
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import uuid
from database import get_db_connection
import asyncpg
from pydantic import BaseModel
from routes.auth import get_current_user, require_supervisor, require_manager

router = APIRouter()

class AttendanceLogCreate(BaseModel):
    person_id: str
    method: str = "manual"  # rfid, face, fingerprint, manual
    location: str = "main_gate"
    status: str = "present"

class CheckOutRequest(BaseModel):
    person_id: str
    location: str = "main_gate"
    notes: Optional[str] = None

@router.post("/check-in")
async def check_in_attendance(
    attendance_data: AttendanceLogCreate,
    current_user: UserProfile = Depends(require_supervisor)
):
    """Record attendance check-in"""
    try:
        conn = await get_db_connection()
        
        # Check if person is already checked in today
        existing_checkin_query = """
        SELECT id, timestamp 
        FROM attendance_logs 
        WHERE person_id = $1 
        AND timestamp >= CURRENT_DATE 
        AND check_out_time IS NULL
        """
        existing = await conn.fetchrow(
            existing_checkin_query, 
            uuid.UUID(attendance_data.person_id)
        )
        
        if existing:
            await conn.close()
            raise HTTPException(
                status_code=400,
                detail="Person is already checked in today"
            )
        
        # Create attendance record
        query = """
        INSERT INTO attendance_logs (
            person_id, method, location, status, timestamp, recorded_by
        ) VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, timestamp
        """
        
        now = datetime.now()
        row = await conn.fetchrow(
            query,
            uuid.UUID(attendance_data.person_id),
            attendance_data.method,
            attendance_data.location,
            attendance_data.status,
            now,
            uuid.UUID(current_user.id)
        )
        
        await conn.close()
        
        return {
            "success": True,
            "data": {
                "attendance_id": str(row['id']),
                "person_id": attendance_data.person_id,
                "check_in_time": row['timestamp'].isoformat(),
                "method": attendance_data.method,
                "location": attendance_data.location
            },
            "message": "Attendance check-in recorded successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid person ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording attendance: {str(e)}")

@router.post("/check-out")
async def check_out_attendance(
    checkout_data: CheckOutRequest,
    current_user: UserProfile = Depends(require_supervisor)
):
    """Record attendance check-out"""
    try:
        conn = await get_db_connection()
        
        # Find the latest check-in for today
        checkin_query = """
        SELECT id, timestamp 
        FROM attendance_logs 
        WHERE person_id = $1 
        AND timestamp >= CURRENT_DATE 
        AND check_out_time IS NULL
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        checkin = await conn.fetchrow(
            checkin_query, 
            uuid.UUID(checkout_data.person_id)
        )
        
        if not checkin:
            await conn.close()
            raise HTTPException(
                status_code=404,
                detail="No active check-in found for this person today"
            )
        
        # Update with check-out time
        update_query = """
        UPDATE attendance_logs 
        SET check_out_time = $1, check_out_location = $2, check_out_notes = $3
        WHERE id = $4
        RETURNING id, timestamp, check_out_time
        """
        
        now = datetime.now()
        row = await conn.fetchrow(
            update_query,
            now,
            checkout_data.location,
            checkout_data.notes,
            checkin['id']
        )
        
        await conn.close()
        
        # Calculate duration
        duration = now - checkin['timestamp']
        hours = duration.total_seconds() / 3600
        
        return {
            "success": True,
            "data": {
                "attendance_id": str(row['id']),
                "person_id": checkout_data.person_id,
                "check_in_time": checkin['timestamp'].isoformat(),
                "check_out_time": row['check_out_time'].isoformat(),
                "duration_hours": round(hours, 2),
                "location": checkout_data.location
            },
            "message": "Attendance check-out recorded successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid person ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording check-out: {str(e)}")

@router.get("/daily-summary")
async def get_daily_attendance_summary(
    summary_date: date = Query(..., description="Date for summary"),
    current_user: UserProfile = Depends(require_manager)
):
    """Get daily attendance summary"""
    try:
        conn = await get_db_connection()
        
        # Use the daily_attendance_sum view if it exists, otherwise calculate
        query = """
        SELECT 
            COUNT(DISTINCT person_id) as total_checked_in,
            COUNT(DISTINCT CASE WHEN check_out_time IS NOT NULL THEN person_id END) as total_checked_out,
            COUNT(DISTINCT CASE WHEN check_out_time IS NULL AND timestamp >= $1 THEN person_id END) as currently_present,
            AVG(EXTRACT(EPOCH FROM (check_out_time - timestamp))/3600) as avg_hours_worked
        FROM attendance_logs 
        WHERE timestamp::date = $1
        """
        
        summary = await conn.fetchrow(query, summary_date)
        
        # Get department-wise breakdown
        dept_query = """
        SELECT 
            pr.person_type as department,
            COUNT(DISTINCT al.person_id) as employee_count,
            AVG(EXTRACT(EPOCH FROM (al.check_out_time - al.timestamp))/3600) as avg_hours
        FROM attendance_logs al
        JOIN person_records pr ON al.person_id = pr.id
        WHERE al.timestamp::date = $1
        GROUP BY pr.person_type
        """
        
        dept_rows = await conn.fetch(dept_query, summary_date)
        
        await conn.close()
        
        department_breakdown = []
        for row in dept_rows:
            department_breakdown.append({
                "department": row['department'],
                "employee_count": row['employee_count'],
                "average_hours": float(row['avg_hours']) if row['avg_hours'] else 0
            })
        
        return {
            "success": True,
            "data": {
                "summary_date": summary_date.isoformat(),
                "total_checked_in": summary['total_checked_in'] or 0,
                "total_checked_out": summary['total_checked_out'] or 0,
                "currently_present": summary['currently_present'] or 0,
                "average_hours_worked": float(summary['avg_hours_worked']) if summary['avg_hours_worked'] else 0,
                "department_breakdown": department_breakdown
            },
            "message": "Daily attendance summary retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving attendance summary: {str(e)}")

@router.get("/person/{person_id}")
async def get_person_attendance(
    person_id: str,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get attendance history for a specific person"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            al.id,
            al.timestamp as check_in_time,
            al.check_out_time,
            al.method,
            al.location,
            al.status,
            EXTRACT(EPOCH FROM (al.check_out_time - al.timestamp))/3600 as hours_worked,
            pr.full_name,
            pr.staff_id
        FROM attendance_logs al
        JOIN person_records pr ON al.person_id = pr.id
        WHERE al.person_id = $1 
        AND al.timestamp::date BETWEEN $2 AND $3
        ORDER BY al.timestamp DESC
        """
        
        rows = await conn.fetch(
            query, 
            uuid.UUID(person_id), 
            start_date, 
            end_date
        )
        
        await conn.close()
        
        attendance_history = []
        total_hours = 0
        present_days = 0
        
        for row in rows:
            hours = float(row['hours_worked']) if row['hours_worked'] else 0
            attendance_history.append({
                "attendance_id": str(row['id']),
                "date": row['check_in_time'].date().isoformat(),
                "check_in_time": row['check_in_time'].isoformat(),
                "check_out_time": row['check_out_time'].isoformat() if row['check_out_time'] else None,
                "method": row['method'],
                "location": row['location'],
                "hours_worked": hours,
                "status": row['status']
            })
            
            if hours > 0:
                total_hours += hours
                present_days += 1
        
        return {
            "success": True,
            "data": {
                "person_id": person_id,
                "staff_id": rows[0]['staff_id'] if rows else None,
                "full_name": rows[0]['full_name'] if rows else None,
                "attendance_history": attendance_history,
                "summary": {
                    "total_days": len(attendance_history),
                    "present_days": present_days,
                    "total_hours": round(total_hours, 2),
                    "average_hours_per_day": round(total_hours / present_days, 2) if present_days > 0 else 0
                }
            },
            "message": f"Retrieved {len(attendance_history)} attendance records"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid person ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving attendance history: {str(e)}")

@router.get("/rfid-scans/recent")
async def get_recent_rfid_scans(
    hours: int = Query(24, description="Hours to look back"),
    current_user: UserProfile = Depends(require_supervisor)
):
    """Get recent RFID scans for monitoring"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            al.id as scan_id,
            pr.staff_id,
            pr.full_name,
            pr.person_type,
            al.timestamp as scan_time,
            al.location,
            al.status,
            al.method
        FROM attendance_logs al
        JOIN person_records pr ON al.person_id = pr.id
        WHERE al.method = 'rfid' 
        AND al.timestamp >= NOW() - INTERVAL '1 hour' * $1
        ORDER BY al.timestamp DESC
        LIMIT 100
        """
        
        rows = await conn.fetch(query, hours)
        await conn.close()
        
        rfid_scans = []
        for row in rows:
            rfid_scans.append({
                "scan_id": str(row['scan_id']),
                "staff_id": row['staff_id'],
                "full_name": row['full_name'],
                "person_type": row['person_type'],
                "scan_time": row['scan_time'].isoformat(),
                "location": row['location'],
                "status": row['status'],
                "method": row['method']
            })
        
        return {
            "success": True,
            "data": rfid_scans,
            "message": f"Retrieved {len(rfid_scans)} recent RFID scans"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving RFID scans: {str(e)}")