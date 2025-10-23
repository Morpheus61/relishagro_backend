# routes/job_types.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from database import get_db
from models.job_type import DailyJobType
from routes.auth import get_current_user, require_manager, UserProfile

router = APIRouter()

# Pydantic models for request validation
class JobTypeCreate(BaseModel):
    job_name: str
    category: str
    unit_of_measurement: str
    expected_output_per_worker: float

class JobTypeUpdate(BaseModel):
    job_name: Optional[str] = None
    category: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    expected_output_per_worker: Optional[float] = None

class DailyJobCreate(BaseModel):
    name: str
    category: str
    unit_of_measurement: str
    expected_output_per_worker: float

class DailyJobUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    expected_output_per_worker: Optional[float] = None

# ============================================================================
# JOB TYPES ROUTES (daily_job_types table)
# ============================================================================

# ✅ NEW ENDPOINT - Added for frontend compatibility
@router.get("/jobs")
def get_jobs(db: Session = Depends(get_db), current_user: UserProfile = Depends(get_current_user)):
    """Get all daily jobs (alias for job-types for frontend compatibility)"""
    try:
        job_types = (
            db.query(DailyJobType)
            .filter(DailyJobType.is_active == True)
            .order_by(DailyJobType.job_name)
            .limit(100)
            .all()
        )
        
        jobs = []
        for jt in job_types:
            jobs.append({
                "id": str(jt.id),
                "name": jt.job_name,
                "category": jt.category,
                "unit": jt.unit_of_measurement,
                "expected_output": float(jt.expected_output_per_worker) if jt.expected_output_per_worker else 0,
                "created_at": jt.created_at.isoformat() if jt.created_at else None
            })
        
        return {
            "success": True,
            "data": jobs,
            "message": f"Retrieved {len(jobs)} jobs successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")

@router.get("/job-types")
def get_daily_job_types(db: Session = Depends(get_db)):
    """Get all job types from daily_job_types table"""
    try:
        job_types = (
            db.query(DailyJobType)
            .filter(DailyJobType.is_active == True)
            .order_by(DailyJobType.created_at.desc())
            .limit(100)
            .all()
        )
        
        daily_job_types = []
        for jt in job_types:
            daily_job_types.append({
                "id": str(jt.id),
                "job_name": jt.job_name,
                "category": jt.category,
                "unit_of_measurement": jt.unit_of_measurement,
                "expected_output_per_worker": float(jt.expected_output_per_worker) if jt.expected_output_per_worker else 0,
                "created_by": str(jt.created_by) if jt.created_by else None,
                "created_at": jt.created_at.isoformat() if jt.created_at else None,
                "updated_at": jt.updated_at.isoformat() if jt.updated_at else None
            })
        
        return {
            "success": True,
            "data": daily_job_types,
            "message": f"Retrieved {len(daily_job_types)} job types successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job types: {str(e)}")

@router.post("/job-types")
def create_job_type(
    job_type: JobTypeCreate, 
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_manager)
):
    """Create a new job type with authenticated user"""
    try:
        # Check if job name already exists
        existing = db.query(DailyJobType).filter(DailyJobType.job_name == job_type.job_name).first()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Job type with name '{job_type.job_name}' already exists"
            )
        
        new_job_type = DailyJobType(
            job_name=job_type.job_name,
            category=job_type.category,
            unit_of_measurement=job_type.unit_of_measurement,
            expected_output_per_worker=job_type.expected_output_per_worker,
            created_by=uuid.UUID(current_user.id),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True
        )
        
        db.add(new_job_type)
        db.commit()
        db.refresh(new_job_type)
        
        return {
            "success": True,
            "data": {
                "id": str(new_job_type.id),
                "job_name": new_job_type.job_name,
                "category": new_job_type.category,
                "unit_of_measurement": new_job_type.unit_of_measurement,
                "expected_output_per_worker": new_job_type.expected_output_per_worker,
                "created_by": str(new_job_type.created_by),
                "created_at": new_job_type.created_at.isoformat(),
                "updated_at": new_job_type.updated_at.isoformat()
            },
            "message": "Job type created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating job type: {str(e)}")


# ============================================================================
# ENHANCED REPORTING ROUTES (Now using SQLAlchemy ORM for compatibility)
# ============================================================================

@router.get("/reports/production")
def get_production_report(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_manager)
):
    """Get production report with data from multiple tables"""
    from sqlalchemy import text, func, and_
    
    try:
        # Production data from lots and processing
        # Since you're using raw SQL, we'll use SQLAlchemy's text() for safety
        production_query = text("""
        SELECT 
            l.crop,
            COUNT(l.lot_id) as total_lots,
            SUM(l.raw_weight) as total_raw_weight,
            SUM(l.threshed_weight) as total_threshed_weight,
            AVG(l.estate_yield_pct) as avg_estate_yield,
            COUNT(fp.process_id) as processed_lots,
            AVG(fp.flavorcore_yield_pct) as avg_flavorcore_yield
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        WHERE l.date_harvested BETWEEN :start AND :end
        GROUP BY l.crop
        ORDER BY total_raw_weight DESC
        """)
        
        production_result = db.execute(production_query, {"start": start_date, "end": end_date}).fetchall()
        
        # Worker productivity from job_completion_summary if available
        productivity_data = None
        try:
            productivity_query = text("""
            SELECT 
                AVG(efficiency_rate) as avg_efficiency,
                COUNT(*) as completed_jobs
            FROM job_completion_summary 
            WHERE date BETWEEN :start AND :end
            """)
            row = db.execute(productivity_query, {"start": start_date, "end": end_date}).fetchone()
            if row:
                productivity_data = {
                    "avg_efficiency": float(row.avg_efficiency) if row.avg_efficiency else 0,
                    "completed_jobs": row.completed_jobs or 0
                }
        except Exception:
            # Table may not exist — that's OK
            pass
        
        # Harvest metrics if available
        harvest_data = []
        try:
            harvest_query = text("""
            SELECT 
                crop_type,
                AVG(yield_per_hectare) as avg_yield,
                AVG(quality_score) as avg_quality
            FROM harvest_metrics
            WHERE harvest_date BETWEEN :start AND :end
            GROUP BY crop_type
            """)
            rows = db.execute(harvest_query, {"start": start_date, "end": end_date}).fetchall()
            for row in rows:
                harvest_data.append({
                    "crop_type": row.crop_type,
                    "avg_yield": float(row.avg_yield) if row.avg_yield else 0,
                    "avg_quality": float(row.avg_quality) if row.avg_quality else 0
                })
        except Exception:
            # Table may not exist — that's OK
            pass
        
        report = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "production_summary": [],
            "productivity": productivity_data or {"note": "Productivity data not available"},
            "harvest_metrics": harvest_data or []
        }
        
        for row in production_result:
            report["production_summary"].append({
                "crop": row.crop,
                "total_lots": row.total_lots,
                "total_raw_weight": float(row.total_raw_weight) if row.total_raw_weight else 0,
                "total_threshed_weight": float(row.total_threshed_weight) if row.total_threshed_weight else 0,
                "avg_estate_yield": float(row.avg_estate_yield) if row.avg_estate_yield else 0,
                "processed_lots": row.processed_lots,
                "avg_flavorcore_yield": float(row.avg_flavorcore_yield) if row.avg_flavorcore_yield else 0
            })
        
        return {
            "success": True,
            "data": report,
            "message": "Production report generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating production report: {str(e)}")