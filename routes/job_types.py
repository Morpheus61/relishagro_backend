from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import get_db_connection
import asyncpg
from pydantic import BaseModel
import uuid

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

async def get_database():
    """Get database connection"""
    try:
        return await get_db_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# ============================================================================
# JOB TYPES ROUTES (daily_job_types table)
# ============================================================================

@router.get("/job-types")
async def get_job_types():
    """Get all job types from daily_job_types table"""
    try:
        conn = await get_database()
        
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
        
        job_types = []
        for row in rows:
            job_types.append({
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
            "data": job_types,
            "message": f"Retrieved {len(job_types)} job types successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job types: {str(e)}")

@router.get("/job-types/{job_type_id}")
async def get_job_type(job_type_id: str):
    """Get specific job type by ID"""
    try:
        conn = await get_database()
        
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
        WHERE id = $1
        """
        
        row = await conn.fetchrow(query, uuid.UUID(job_type_id))
        await conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Job type not found")
        
        job_type = {
            "id": str(row['id']),
            "job_name": row['job_name'],
            "category": row['category'],
            "unit_of_measurement": row['unit_of_measurement'],
            "expected_output_per_worker": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0,
            "created_by": str(row['created_by']) if row['created_by'] else None,
            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
            "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
        }
        
        return {
            "success": True,
            "data": job_type,
            "message": "Job type retrieved successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job type ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job type: {str(e)}")

@router.post("/job-types")
async def create_job_type(job_type: JobTypeCreate):
    """Create a new job type"""
    try:
        conn = await get_database()
        
        # Check if job name already exists
        check_query = "SELECT id FROM daily_job_types WHERE job_name = $1"
        existing = await conn.fetchval(check_query, job_type.job_name)
        
        if existing:
            await conn.close()
            raise HTTPException(status_code=400, detail=f"Job type with name '{job_type.job_name}' already exists")
        
        query = """
        INSERT INTO daily_job_types (
            job_name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_at,
            updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, created_at
        """
        
        now = datetime.now()
        row = await conn.fetchrow(
            query,
            job_type.job_name,
            job_type.category,
            job_type.unit_of_measurement,
            job_type.expected_output_per_worker,
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
            "created_at": row['created_at'].isoformat(),
            "updated_at": row['created_at'].isoformat()
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

@router.put("/job-types/{job_type_id}")
async def update_job_type(job_type_id: str, job_type_update: JobTypeUpdate):
    """Update an existing job type"""
    try:
        conn = await get_database()
        
        # Check if job type exists
        check_query = "SELECT id FROM daily_job_types WHERE id = $1"
        existing = await conn.fetchval(check_query, uuid.UUID(job_type_id))
        
        if not existing:
            await conn.close()
            raise HTTPException(status_code=404, detail="Job type not found")
        
        # Build dynamic update query
        update_fields = []
        values = []
        param_count = 1
        
        if job_type_update.job_name is not None:
            # Check for duplicate name (excluding current record)
            duplicate_check = "SELECT id FROM daily_job_types WHERE job_name = $1 AND id != $2"
            duplicate = await conn.fetchval(duplicate_check, job_type_update.job_name, uuid.UUID(job_type_id))
            if duplicate:
                await conn.close()
                raise HTTPException(status_code=400, detail=f"Job type with name '{job_type_update.job_name}' already exists")
            
            update_fields.append(f"job_name = ${param_count}")
            values.append(job_type_update.job_name)
            param_count += 1
        
        if job_type_update.category is not None:
            update_fields.append(f"category = ${param_count}")
            values.append(job_type_update.category)
            param_count += 1
        
        if job_type_update.unit_of_measurement is not None:
            update_fields.append(f"unit_of_measurement = ${param_count}")
            values.append(job_type_update.unit_of_measurement)
            param_count += 1
        
        if job_type_update.expected_output_per_worker is not None:
            update_fields.append(f"expected_output_per_worker = ${param_count}")
            values.append(job_type_update.expected_output_per_worker)
            param_count += 1
        
        if not update_fields:
            await conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add updated_at
        update_fields.append(f"updated_at = ${param_count}")
        values.append(datetime.now())
        param_count += 1
        
        # Add ID for WHERE clause
        values.append(uuid.UUID(job_type_id))
        
        query = f"""
        UPDATE daily_job_types 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count}
        RETURNING id, job_name, category, unit_of_measurement, expected_output_per_worker, created_at, updated_at
        """
        
        row = await conn.fetchrow(query, *values)
        await conn.close()
        
        updated_job_type = {
            "id": str(row['id']),
            "job_name": row['job_name'],
            "category": row['category'],
            "unit_of_measurement": row['unit_of_measurement'],
            "expected_output_per_worker": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0,
            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
            "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
        }
        
        return {
            "success": True,
            "data": updated_job_type,
            "message": "Job type updated successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job type ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating job type: {str(e)}")

@router.delete("/job-types/{job_type_id}")
async def delete_job_type(job_type_id: str):
    """Delete a job type"""
    try:
        conn = await get_database()
        
        # Check if job type exists and get its details
        check_query = """
        SELECT id, job_name 
        FROM daily_job_types 
        WHERE id = $1
        """
        existing = await conn.fetchrow(check_query, uuid.UUID(job_type_id))
        
        if not existing:
            await conn.close()
            raise HTTPException(status_code=404, detail="Job type not found")
        
        # Check if job type is being used in daily_jobs
        usage_check = "SELECT COUNT(*) FROM daily_jobs WHERE name = $1"
        usage_count = await conn.fetchval(usage_check, existing['job_name'])
        
        if usage_count > 0:
            await conn.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete job type '{existing['job_name']}' as it is being used in {usage_count} daily job(s)"
            )
        
        # Delete the job type
        delete_query = "DELETE FROM daily_job_types WHERE id = $1"
        await conn.execute(delete_query, uuid.UUID(job_type_id))
        await conn.close()
        
        return {
            "success": True,
            "message": f"Job type '{existing['job_name']}' deleted successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job type ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting job type: {str(e)}")

# ============================================================================
# DAILY JOBS ROUTES (daily_jobs table)
# ============================================================================

@router.get("/daily-jobs")
async def get_daily_jobs():
    """Get all daily jobs from daily_jobs table"""
    try:
        conn = await get_database()
        
        query = """
        SELECT 
            id,
            name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_by,
            created_at
        FROM daily_jobs
        ORDER BY created_at DESC
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        daily_jobs = []
        for row in rows:
            daily_jobs.append({
                "id": str(row['id']),
                "name": row['name'],
                "category": row['category'],
                "unit_of_measurement": row['unit_of_measurement'],
                "expected_output_per_worker": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0,
                "created_by": str(row['created_by']) if row['created_by'] else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            })
        
        return {
            "success": True,
            "data": daily_jobs,
            "message": f"Retrieved {len(daily_jobs)} daily jobs successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving daily jobs: {str(e)}")

@router.get("/daily-jobs/{daily_job_id}")
async def get_daily_job(daily_job_id: str):
    """Get specific daily job by ID"""
    try:
        conn = await get_database()
        
        query = """
        SELECT 
            id,
            name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_by,
            created_at
        FROM daily_jobs
        WHERE id = $1
        """
        
        row = await conn.fetchrow(query, uuid.UUID(daily_job_id))
        await conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Daily job not found")
        
        daily_job = {
            "id": str(row['id']),
            "name": row['name'],
            "category": row['category'],
            "unit_of_measurement": row['unit_of_measurement'],
            "expected_output_per_worker": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0,
            "created_by": str(row['created_by']) if row['created_by'] else None,
            "created_at": row['created_at'].isoformat() if row['created_at'] else None
        }
        
        return {
            "success": True,
            "data": daily_job,
            "message": "Daily job retrieved successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid daily job ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving daily job: {str(e)}")

@router.post("/daily-jobs")
async def create_daily_job(daily_job: DailyJobCreate):
    """Create a new daily job"""
    try:
        conn = await get_database()
        
        query = """
        INSERT INTO daily_jobs (
            name,
            category,
            unit_of_measurement,
            expected_output_per_worker,
            created_at
        ) VALUES ($1, $2, $3, $4, $5)
        RETURNING id, created_at
        """
        
        now = datetime.now()
        row = await conn.fetchrow(
            query,
            daily_job.name,
            daily_job.category,
            daily_job.unit_of_measurement,
            daily_job.expected_output_per_worker,
            now
        )
        
        await conn.close()
        
        new_daily_job = {
            "id": str(row['id']),
            "name": daily_job.name,
            "category": daily_job.category,
            "unit_of_measurement": daily_job.unit_of_measurement,
            "expected_output_per_worker": daily_job.expected_output_per_worker,
            "created_at": row['created_at'].isoformat()
        }
        
        return {
            "success": True,
            "data": new_daily_job,
            "message": "Daily job created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating daily job: {str(e)}")

@router.put("/daily-jobs/{daily_job_id}")
async def update_daily_job(daily_job_id: str, daily_job_update: DailyJobUpdate):
    """Update an existing daily job"""
    try:
        conn = await get_database()
        
        # Check if daily job exists
        check_query = "SELECT id FROM daily_jobs WHERE id = $1"
        existing = await conn.fetchval(check_query, uuid.UUID(daily_job_id))
        
        if not existing:
            await conn.close()
            raise HTTPException(status_code=404, detail="Daily job not found")
        
        # Build dynamic update query
        update_fields = []
        values = []
        param_count = 1
        
        if daily_job_update.name is not None:
            update_fields.append(f"name = ${param_count}")
            values.append(daily_job_update.name)
            param_count += 1
        
        if daily_job_update.category is not None:
            update_fields.append(f"category = ${param_count}")
            values.append(daily_job_update.category)
            param_count += 1
        
        if daily_job_update.unit_of_measurement is not None:
            update_fields.append(f"unit_of_measurement = ${param_count}")
            values.append(daily_job_update.unit_of_measurement)
            param_count += 1
        
        if daily_job_update.expected_output_per_worker is not None:
            update_fields.append(f"expected_output_per_worker = ${param_count}")
            values.append(daily_job_update.expected_output_per_worker)
            param_count += 1
        
        if not update_fields:
            await conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add ID for WHERE clause
        values.append(uuid.UUID(daily_job_id))
        
        query = f"""
        UPDATE daily_jobs 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count}
        RETURNING id, name, category, unit_of_measurement, expected_output_per_worker, created_at
        """
        
        row = await conn.fetchrow(query, *values)
        await conn.close()
        
        updated_daily_job = {
            "id": str(row['id']),
            "name": row['name'],
            "category": row['category'],
            "unit_of_measurement": row['unit_of_measurement'],
            "expected_output_per_worker": float(row['expected_output_per_worker']) if row['expected_output_per_worker'] else 0,
            "created_at": row['created_at'].isoformat() if row['created_at'] else None
        }
        
        return {
            "success": True,
            "data": updated_daily_job,
            "message": "Daily job updated successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid daily job ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating daily job: {str(e)}")

@router.delete("/daily-jobs/{daily_job_id}")
async def delete_daily_job(daily_job_id: str):
    """Delete a daily job"""
    try:
        conn = await get_database()
        
        # Check if daily job exists and get its details
        check_query = """
        SELECT id, name 
        FROM daily_jobs 
        WHERE id = $1
        """
        existing = await conn.fetchrow(check_query, uuid.UUID(daily_job_id))
        
        if not existing:
            await conn.close()
            raise HTTPException(status_code=404, detail="Daily job not found")
        
        # Check if daily job is being used in activity_logs
        usage_check = """
        SELECT COUNT(*) 
        FROM activity_logs al
        JOIN daily_jobs dj ON al.job_id = dj.id
        WHERE dj.id = $1
        """
        usage_count = await conn.fetchval(usage_check, uuid.UUID(daily_job_id))
        
        if usage_count > 0:
            await conn.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete daily job '{existing['name']}' as it is being used in {usage_count} activity log(s)"
            )
        
        # Delete the daily job
        delete_query = "DELETE FROM daily_jobs WHERE id = $1"
        await conn.execute(delete_query, uuid.UUID(daily_job_id))
        await conn.close()
        
        return {
            "success": True,
            "message": f"Daily job '{existing['name']}' deleted successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid daily job ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting daily job: {str(e)}")

# ============================================================================
# COMBINED STATISTICS ROUTES
# ============================================================================

@router.get("/job-statistics")
async def get_job_statistics():
    """Get combined statistics for job types and daily jobs"""
    try:
        conn = await get_database()
        
        # Get job types count by category
        job_types_query = """
        SELECT category, COUNT(*) as count
        FROM daily_job_types
        GROUP BY category
        ORDER BY count DESC
        """
        
        # Get daily jobs count by category
        daily_jobs_query = """
        SELECT category, COUNT(*) as count
        FROM daily_jobs
        GROUP BY category
        ORDER BY count DESC
        """
        
        # Get recent activity
        recent_activity_query = """
        SELECT 
            'job_type' as type,
            job_name as name,
            category,
            created_at
        FROM daily_job_types
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        UNION ALL
        SELECT 
            'daily_job' as type,
            name,
            category,
            created_at
        FROM daily_jobs
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        job_types_stats = await conn.fetch(job_types_query)
        daily_jobs_stats = await conn.fetch(daily_jobs_query)
        recent_activity = await conn.fetch(recent_activity_query)
        
        await conn.close()
        
        statistics = {
            "job_types_by_category": [
                {"category": row['category'], "count": row['count']} 
                for row in job_types_stats
            ],
            "daily_jobs_by_category": [
                {"category": row['category'], "count": row['count']} 
                for row in daily_jobs_stats
            ],
            "recent_activity": [
                {
                    "type": row['type'],
                    "name": row['name'],
                    "category": row['category'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                }
                for row in recent_activity
            ]
        }
        
        return {
            "success": True,
            "data": statistics,
            "message": "Job statistics retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job statistics: {str(e)}")