# routes/daily_job_types.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from database import get_db_connection
import asyncpg
from pydantic import BaseModel
import uuid
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
async def get_jobs(current_user: UserProfile = Depends(get_current_user)):
    """Get all daily jobs (alias for job-types for frontend compatibility)"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            id,
            job_name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_by,
            created_at,
            updated_at
        FROM daily_job_types
        ORDER BY job_name
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        jobs = []
        for row in rows:
            jobs.append({
                "id": str(row['id']),
                "name": row['job_name'],
                "category": row['category'],
                "unit": row['unit_of_measurement'],
                "expected_output": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            })
        
        return {
            "success": True,
            "data": jobs,
            "message": f"Retrieved {len(jobs)} jobs successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")

@router.get("/job-types")
async def get_daily_job_types():
    """Get all job types from daily_job_types table"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            id,
            job_name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_by,
            created_at,
            updated_at
        FROM daily_job_types
        ORDER BY created_at DESC
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        daily_job_types = []
        for row in rows:
            daily_job_types.append({
                "id": str(row['id']),
                "job_name": row['job_name'],
                "category": row['category'],
                "unit_of_measurement": row['unit_of_measurement'],
                "expected_output_per_worker": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0,
                "created_by": str(row['created_by']) if row['created_by'] else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            })
        
        return {
            "success": True,
            "data": daily_job_types,
            "message": f"Retrieved {len(daily_job_types)} job types successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job types: {str(e)}")

@router.post("/job-types")
async def create_job_type(
    job_type: JobTypeCreate, 
    current_user: UserProfile = Depends(require_manager)
):
    """Create a new job type with authenticated user"""
    try:
        conn = await get_db_connection()
        
        # Check if job name already exists
        check_query = "SELECT id FROM daily_job_types WHERE job_name = $1"
        existing = await conn.fetchval(check_query, job_type.job_name)
        
        if existing:
            await conn.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Job type with name '{job_type.job_name}' already exists"
            )
        
        query = """
        INSERT INTO daily_job_types (
            job_name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_by,
            created_at,
            updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, created_at, updated_at
        """
        
        now = datetime.now()
        row = await conn.fetchrow(
            query,
            job_type.job_name,
            job_type.category,
            job_type.unit_of_measurement,
            job_type.expected_output_per_worker,
            uuid.UUID(current_user.id),
            now,
            now
        )
        
        await conn.close()
        
        new_job_type = {
            "id": str(row['id']),
            "job_name": job_type.job_name,
            "category": job_type.category,
            "unit_of_measurement": job_type.unit_of_measurement,
            "expected_output_per_worker": job_type.expected_output_per_worker,
            "created_by": str(current_user.id),
            "created_at": row['created_at'].isoformat(),
            "updated_at": row['updated_at'].isoformat()
        }
        
        return {
            "success": True,
            "data": new_job_type,
            "message": "Job type created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating job type: {str(e)}")

# ============================================================================
# ENHANCED REPORTING ROUTES
# ============================================================================

@router.get("/reports/production")
async def get_production_report(
    start_date: date,
    end_date: date,
    current_user: UserProfile = Depends(require_manager)
):
    """Get production report with data from multiple tables"""
    try:
        conn = await get_db_connection()
        
        # Production data from lots and processing
        production_query = """
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
        WHERE l.date_harvested BETWEEN $1 AND $2
        GROUP BY l.crop
        ORDER BY total_raw_weight DESC
        """
        
        production_data = await conn.fetch(production_query, start_date, end_date)
        
        # Worker productivity from job_completion_summary if available
        try:
            productivity_query = """
            SELECT 
                AVG(efficiency_rate) as avg_efficiency,
                COUNT(*) as completed_jobs
            FROM job_completion_summary 
            WHERE date BETWEEN $1 AND $2
            """
            productivity_data = await conn.fetchrow(productivity_query, start_date, end_date)
        except:
            productivity_data = None
        
        # Harvest metrics if available
        try:
            harvest_query = """
            SELECT 
                crop_type,
                AVG(yield_per_hectare) as avg_yield,
                AVG(quality_score) as avg_quality
            FROM harvest_metrics
            WHERE harvest_date BETWEEN $1 AND $2
            GROUP BY crop_type
            """
            harvest_data = await conn.fetch(harvest_query, start_date, end_date)
        except:
            harvest_data = []
        
        await conn.close()
        
        report = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "production_summary": [],
            "productivity": {
                "avg_efficiency": productivity_data['avg_efficiency'] if productivity_data else 0,
                "completed_jobs": productivity_data['completed_jobs'] if productivity_data else 0
            } if productivity_data else {"note": "Productivity data not available"},
            "harvest_metrics": [
                {
                    "crop_type": row['crop_type'],
                    "avg_yield": float(row['avg_yield']) if row['avg_yield'] else 0,
                    "avg_quality": float(row['avg_quality']) if row['avg_quality'] else 0
                } for row in harvest_data
            ] if harvest_data else []
        }
        
        for row in production_data:
            report["production_summary"].append({
                "crop": row['crop'],
                "total_lots": row['total_lots'],
                "total_raw_weight": float(row['total_raw_weight']) if row['total_raw_weight'] else 0,
                "total_threshed_weight": float(row['total_threshed_weight']) if row['total_threshed_weight'] else 0,
                "avg_estate_yield": float(row['avg_estate_yield']) if row['avg_estate_yield'] else 0,
                "processed_lots": row['processed_lots'],
                "avg_flavorcore_yield": float(row['avg_flavorcore_yield']) if row['avg_flavorcore_yield'] else 0
            })
        
        return {
            "success": True,
            "data": report,
            "message": "Production report generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating production report: {str(e)}")