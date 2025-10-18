# routes/supervisor.py
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from database import get_db_connection
import asyncpg
from pydantic import BaseModel
import uuid
import json
from routes.auth import get_current_user, require_supervisor
from services.notification_service import notification_service

router = APIRouter()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class QualityTestCreate(BaseModel):
    lot_id: str
    in_scan_weight: float
    sample_tests: Dict[str, Any]
    handled_by: str
    supervisor_notes: Optional[str] = None

class QualityTestUpdate(BaseModel):
    in_scan_weight: Optional[float] = None
    sample_tests: Optional[Dict[str, Any]] = None
    flavorcore_yield_pct: Optional[float] = None
    total_yield_pct: Optional[float] = None
    status: Optional[str] = None
    supervisor_notes: Optional[str] = None

class WorkerAssignmentCreate(BaseModel):
    person_id: str
    location: str = "main_gate"
    assignment_type: str = "daily_work"
    assigned_jobs: Optional[List[str]] = None

class PackedProductSubmit(BaseModel):
    lot_id: str
    quantity_packed: float
    packaging_type: str
    quality_grade: str
    supervisor_notes: Optional[str] = None

# ============================================================================
# EXISTING ENDPOINTS WITH NOTIFICATION INTEGRATION
# ============================================================================

@router.get("/lots")
async def get_lots():
    """Get all production lots from real database - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        # Query lots table with additional status from flavorcore_processing
        query = """
        SELECT 
            l.lot_id,
            l.crop,
            l.raw_weight,
            l.threshed_weight,
            l.estate_yield_pct,
            l.date_harvested,
            l.workers_involved,
            CASE 
                WHEN fp.status IS NOT NULL THEN fp.status
                ELSE 'pending'
            END as status,
            l.created_by,
            l.half_day_weight,
            l.full_day_weight
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        ORDER BY l.date_harvested DESC
        LIMIT 50
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        lots_data = []
        for row in rows:
            lots_data.append({
                "lot_id": row['lot_id'],
                "crop": row['crop'],
                "raw_weight": float(row['raw_weight']) if row['raw_weight'] else 0,
                "threshed_weight": float(row['threshed_weight']) if row['threshed_weight'] else 0,
                "estate_yield_pct": float(row['estate_yield_pct']) if row['estate_yield_pct'] else 0,
                "date_harvested": row['date_harvested'].isoformat() if row['date_harvested'] else None,
                "workers_involved": row['workers_involved'] or [],
                "status": row['status'],
                "half_day_weight": float(row['half_day_weight']) if row['half_day_weight'] else 0,
                "full_day_weight": float(row['full_day_weight']) if row['full_day_weight'] else 0
            })
        
        return {
            "success": True,
            "data": lots_data,
            "message": f"Retrieved {len(lots_data)} lots successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving lots: {str(e)}")

@router.get("/lots/{lot_id}")
async def get_lot_details(lot_id: str):
    """Get detailed information about a specific lot - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            l.*,
            fp.process_id,
            fp.in_scan_weight,
            fp.flavorcore_yield_pct,
            fp.total_yield_pct,
            fp.processed_date,
            fp.status as processing_status
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        WHERE l.lot_id = $1
        """
        
        row = await conn.fetchrow(query, lot_id)
        await conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Lot not found")
        
        lot_detail = {
            "lot_id": row['lot_id'],
            "crop": row['crop'],
            "raw_weight": float(row['raw_weight']) if row['raw_weight'] else 0,
            "threshed_weight": float(row['threshed_weight']) if row['threshed_weight'] else 0,
            "estate_yield_pct": float(row['estate_yield_pct']) if row['estate_yield_pct'] else 0,
            "date_harvested": row['date_harvested'].isoformat() if row['date_harvested'] else None,
            "workers_involved": row['workers_involved'] or [],
            "processing": {
                "process_id": row['process_id'],
                "in_scan_weight": float(row['in_scan_weight']) if row['in_scan_weight'] else 0,
                "flavorcore_yield_pct": float(row['flavorcore_yield_pct']) if row['flavorcore_yield_pct'] else 0,
                "total_yield_pct": float(row['total_yield_pct']) if row['total_yield_pct'] else 0,
                "processed_date": row['processed_date'].isoformat() if row['processed_date'] else None,
                "status": row['processing_status']
            } if row['process_id'] else None
        }
        
        return {
            "success": True,
            "data": lot_detail,
            "message": "Lot details retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving lot details: {str(e)}")

@router.get("/quality-tests")
async def get_quality_tests():
    """Get all quality test results from flavorcore_processing table - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            fp.process_id,
            fp.lot_id,
            fp.in_scan_weight,
            fp.flavorcore_yield_pct,
            fp.total_yield_pct,
            fp.processed_date,
            fp.status,
            fp.sample_tests,
            fp.handled_by,
            fp.supervisor_id,
            l.crop
        FROM flavorcore_processing fp
        LEFT JOIN lots l ON fp.lot_id = l.lot_id
        ORDER BY fp.processed_date DESC
        LIMIT 100
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        quality_tests = []
        for row in rows:
            quality_tests.append({
                "process_id": row['process_id'],
                "lot_id": row['lot_id'],
                "crop": row['crop'],
                "in_scan_weight": float(row['in_scan_weight']) if row['in_scan_weight'] else 0,
                "flavorcore_yield_pct": float(row['flavorcore_yield_pct']) if row['flavorcore_yield_pct'] else 0,
                "total_yield_pct": float(row['total_yield_pct']) if row['total_yield_pct'] else 0,
                "processed_date": row['processed_date'].isoformat() if row['processed_date'] else None,
                "status": row['status'] or 'pending',
                "sample_tests": row['sample_tests'] or {},
                "handled_by": row['handled_by'],
                "supervisor_id": row['supervisor_id']
            })
        
        return {
            "success": True,
            "data": quality_tests,
            "message": f"Retrieved {len(quality_tests)} quality tests successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving quality tests: {str(e)}")

@router.post("/quality-tests")
async def create_quality_test(test_data: Dict[str, Any]):
    """Create a new quality test record - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        query = """
        INSERT INTO flavorcore_processing (
            lot_id, in_scan_weight, handled_by, supervisor_id, 
            sample_tests, status, processed_date
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING process_id
        """
        
        process_id = await conn.fetchval(
            query,
            test_data.get("lot_id"),
            test_data.get("in_scan_weight", 0),
            test_data.get("handled_by"),
            test_data.get("supervisor_id"),
            test_data.get("sample_tests", {}),
            test_data.get("status", "pending"),
            datetime.now()
        )
        
        await conn.close()
        
        return {
            "success": True,
            "data": {
                "process_id": process_id,
                "message": "Quality test created successfully"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating quality test: {str(e)}")

@router.get("/worker-assignments")
async def get_worker_assignments():
    """Get worker assignments from attendance_logs and person_records - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            al.id,
            al.person_id,
            pr.full_name,
            pr.staff_id,
            al.timestamp,
            al.location,
            al.status,
            al.method,
            al.check_out_time
        FROM attendance_logs al
        JOIN person_records pr ON al.person_id = pr.id
        WHERE al.timestamp >= CURRENT_DATE
        ORDER BY al.timestamp DESC
        LIMIT 50
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        worker_assignments = []
        for row in rows:
            worker_assignments.append({
                "id": str(row['id']),
                "person_id": str(row['person_id']),
                "full_name": row['full_name'],
                "staff_id": row['staff_id'],
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                "location": row['location'] or 'main_gate',
                "status": row['status'] or 'present',
                "method": row['method'],
                "check_out_time": row['check_out_time'].isoformat() if row['check_out_time'] else None
            })
        
        return {
            "success": True,
            "data": worker_assignments,
            "message": f"Retrieved {len(worker_assignments)} worker assignments successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving worker assignments: {str(e)}")

@router.post("/worker-assignments")
async def assign_worker(assignment_data: Dict[str, Any]):
    """Create a new worker assignment via attendance log - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        query = """
        INSERT INTO attendance_logs (
            person_id, method, location, status, timestamp
        ) VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """
        
        assignment_id = await conn.fetchval(
            query,
            assignment_data.get("person_id"),
            assignment_data.get("method", "manual"),
            assignment_data.get("location", "main_gate"),
            assignment_data.get("status", "present"),
            datetime.now()
        )
        
        await conn.close()
        
        return {
            "success": True,
            "data": {
                "id": str(assignment_id),
                "message": "Worker assigned successfully"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning worker: {str(e)}")

@router.post("/submit-packed-products")
async def submit_packed_products(submission_data: Dict[str, Any]):
    """Submit packed products - update flavorcore_processing status - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        # Update the processing record
        query = """
        UPDATE flavorcore_processing 
        SET status = 'submitted', 
            submitted_at = $1,
            supervisor_id = $2
        WHERE lot_id = $3
        RETURNING process_id
        """
        
        process_id = await conn.fetchval(
            query,
            datetime.now(),
            submission_data.get("supervisor_id"),
            submission_data.get("lot_id")
        )
        
        await conn.close()
        
        if not process_id:
            raise HTTPException(status_code=404, detail="Processing record not found for this lot")
        
        submission = {
            "submission_id": f"SUB{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "process_id": str(process_id),
            "lot_id": submission_data.get("lot_id"),
            "quantity_packed": submission_data.get("quantity_packed"),
            "supervisor_id": submission_data.get("supervisor_id"),
            "submission_date": datetime.now().isoformat(),
            "status": "submitted",
            "notes": submission_data.get("notes", "")
        }
        
        return {
            "success": True,
            "data": submission,
            "message": "Packed products submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting packed products: {str(e)}")

@router.get("/rfid-scans")
async def get_rfid_scans():
    """Get recent RFID scan data from attendance_logs - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            al.id as scan_id,
            pr.staff_id as rfid_tag,
            pr.id as worker_id,
            pr.full_name as worker_name,
            al.timestamp as scan_time,
            al.location,
            al.status
        FROM attendance_logs al
        JOIN person_records pr ON al.person_id = pr.id
        WHERE al.method = 'rfid' 
        AND al.timestamp >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY al.timestamp DESC
        LIMIT 50
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        rfid_scans = []
        for row in rows:
            rfid_scans.append({
                "scan_id": str(row['scan_id']),
                "rfid_tag": row['rfid_tag'],
                "worker_id": str(row['worker_id']),
                "worker_name": row['worker_name'],
                "scan_time": row['scan_time'].isoformat() if row['scan_time'] else None,
                "location": row['location'] or 'main_gate',
                "status": row['status'] or 'present'
            })
        
        return {
            "success": True,
            "data": rfid_scans,
            "message": f"Retrieved {len(rfid_scans)} RFID scans successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving RFID scans: {str(e)}")

@router.get("/process-monitoring")
async def get_process_monitoring():
    """Get real-time process monitoring data from database - YOUR EXISTING ENDPOINT"""
    try:
        conn = await get_db_connection()
        
        # Get active lots count
        active_lots_query = """
        SELECT COUNT(*) as count 
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        WHERE fp.status IN ('in_progress', 'pending') OR fp.status IS NULL
        """
        
        # Get active workers today
        active_workers_query = """
        SELECT COUNT(DISTINCT person_id) as count
        FROM attendance_logs 
        WHERE timestamp >= CURRENT_DATE 
        AND status = 'present'
        AND check_out_time IS NULL
        """
        
        # Get quality tests today
        quality_tests_today_query = """
        SELECT COUNT(*) as count
        FROM flavorcore_processing 
        WHERE processed_date = CURRENT_DATE
        """
        
        # Get efficiency calculation (example: completed vs total)
        efficiency_query = """
        SELECT 
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(*) as total
        FROM flavorcore_processing 
        WHERE processed_date >= CURRENT_DATE - INTERVAL '7 days'
        """
        
        active_lots = await conn.fetchval(active_lots_query)
        active_workers = await conn.fetchval(active_workers_query)
        quality_tests_today = await conn.fetchval(quality_tests_today_query)
        efficiency_row = await conn.fetchrow(efficiency_query)
        
        await conn.close()
        
        # Calculate efficiency percentage
        efficiency = 0
        if efficiency_row['total'] > 0:
            efficiency = (efficiency_row['completed'] / efficiency_row['total']) * 100
        
        monitoring_data = {
            "active_lots": active_lots or 0,
            "total_workers_active": active_workers or 0,
            "quality_tests_today": quality_tests_today or 0,
            "production_efficiency": round(efficiency, 1),
            "quality_pass_rate": 95.2  # Could be calculated from sample_tests data
        }
        
        return {
            "success": True,
            "data": monitoring_data,
            "message": "Process monitoring data retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving process monitoring data: {str(e)}")

# ============================================================================
# NEW ENHANCED FEATURES WITH NOTIFICATION INTEGRATION
# ============================================================================

@router.get("/dashboard/overview")
async def get_supervisor_dashboard(current_user = Depends(require_supervisor)):
    """Get supervisor-specific dashboard overview - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        # Get supervisor's active lots
        active_lots_query = """
        SELECT COUNT(*) as count 
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        WHERE (fp.status IN ('in_progress', 'pending') OR fp.status IS NULL)
        AND l.date_harvested >= CURRENT_DATE - INTERVAL '30 days'
        """
        
        # Get workers under supervisor today
        active_workers_query = """
        SELECT COUNT(DISTINCT al.person_id) as count
        FROM attendance_logs al
        JOIN person_records pr ON al.person_id = pr.id
        WHERE al.timestamp >= CURRENT_DATE 
        AND al.status = 'present'
        AND al.check_out_time IS NULL
        AND pr.person_type IN ('harvesting', 'staff')
        """
        
        # Get pending quality tests
        pending_tests_query = """
        SELECT COUNT(*) as count
        FROM flavorcore_processing 
        WHERE status = 'pending'
        AND processed_date >= CURRENT_DATE - INTERVAL '7 days'
        """
        
        # Get today's production summary
        production_summary_query = """
        SELECT 
            COUNT(*) as total_lots,
            COALESCE(SUM(raw_weight), 0) as total_raw_weight,
            COALESCE(SUM(threshed_weight), 0) as total_threshed_weight
        FROM lots
        WHERE date_harvested = CURRENT_DATE
        """
        
        active_lots = await conn.fetchval(active_lots_query)
        active_workers = await conn.fetchval(active_workers_query)
        pending_tests = await conn.fetchval(pending_tests_query)
        production_summary = await conn.fetchrow(production_summary_query)
        
        await conn.close()
        
        dashboard_data = {
            "supervisor": {
                "staff_id": current_user.staff_id,
                "role": current_user.role
            },
            "overview": {
                "active_lots": active_lots or 0,
                "workers_onsite": active_workers or 0,
                "pending_quality_tests": pending_tests or 0,
                "today_production": {
                    "total_lots": production_summary['total_lots'] or 0,
                    "total_raw_weight": float(production_summary['total_raw_weight']) or 0,
                    "total_threshed_weight": float(production_summary['total_threshed_weight']) or 0
                }
            },
            "quick_actions": [
                {"action": "assign_workers", "label": "Assign Workers", "icon": "👥"},
                {"action": "quality_test", "label": "Quality Test", "icon": "🔍"},
                {"action": "submit_products", "label": "Submit Products", "icon": "📦"},
                {"action": "view_reports", "label": "View Reports", "icon": "📊"}
            ]
        }
        
        return {
            "success": True,
            "data": dashboard_data,
            "message": "Supervisor dashboard data retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving supervisor dashboard: {str(e)}")

@router.get("/lots/enhanced")
async def get_supervisor_lots(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    crop_type: Optional[str] = Query(None, description="Filter by crop type"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    current_user = Depends(require_supervisor)
):
    """Get production lots with supervisor-specific filters - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        # Build query with filters
        where_conditions = []
        params = []
        param_count = 1
        
        if status_filter:
            if status_filter == "pending_processing":
                where_conditions.append("fp.status IS NULL")
            elif status_filter == "in_progress":
                where_conditions.append("fp.status = 'in_progress'")
            elif status_filter == "completed":
                where_conditions.append("fp.status = 'completed'")
            elif status_filter == "needs_attention":
                where_conditions.append("fp.status IN ('failed', 'needs_review')")
        
        if crop_type:
            where_conditions.append(f"l.crop = ${param_count}")
            params.append(crop_type)
            param_count += 1
            
        if date_from:
            where_conditions.append(f"l.date_harvested >= ${param_count}")
            params.append(date_from)
            param_count += 1
            
        if date_to:
            where_conditions.append(f"l.date_harvested <= ${param_count}")
            params.append(date_to)
            param_count += 1
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        query = f"""
        SELECT 
            l.lot_id,
            l.crop,
            l.raw_weight,
            l.threshed_weight,
            l.estate_yield_pct,
            l.date_harvested,
            l.workers_involved,
            COALESCE(fp.status, 'pending') as processing_status,
            fp.process_id,
            l.half_day_weight,
            l.full_day_weight,
            fp.supervisor_id,
            fp.processed_date
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        {where_clause}
        ORDER BY l.date_harvested DESC
        LIMIT 100
        """
        
        rows = await conn.fetch(query, *params)
        await conn.close()
        
        lots_data = []
        for row in rows:
            lots_data.append({
                "lot_id": row['lot_id'],
                "crop": row['crop'],
                "raw_weight": float(row['raw_weight']) if row['raw_weight'] else 0,
                "threshed_weight": float(row['threshed_weight']) if row['threshed_weight'] else 0,
                "estate_yield_pct": float(row['estate_yield_pct']) if row['estate_yield_pct'] else 0,
                "date_harvested": row['date_harvested'].isoformat() if row['date_harvested'] else None,
                "workers_involved": row['workers_involved'] or [],
                "status": row['processing_status'],
                "process_id": row['process_id'],
                "supervisor_id": str(row['supervisor_id']) if row['supervisor_id'] else None,
                "processed_date": row['processed_date'].isoformat() if row['processed_date'] else None,
                "half_day_weight": float(row['half_day_weight']) if row['half_day_weight'] else 0,
                "full_day_weight": float(row['full_day_weight']) if row['full_day_weight'] else 0
            })
        
        return {
            "success": True,
            "data": lots_data,
            "message": f"Retrieved {len(lots_data)} lots successfully",
            "filters_applied": {
                "status": status_filter,
                "crop_type": crop_type,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving lots: {str(e)}")

@router.get("/quality-tests/enhanced")
async def get_supervisor_quality_tests(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user = Depends(require_supervisor)
):
    """Get quality test results with supervisor context - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        # Build query with filters
        where_conditions = []
        params = []
        param_count = 1
        
        if status:
            where_conditions.append(f"fp.status = ${param_count}")
            params.append(status)
            param_count += 1
        
        # Add supervisor filter to see tests they handled or are assigned to them
        where_conditions.append(f"(fp.supervisor_id = ${param_count} OR fp.handled_by = ${param_count})")
        params.append(current_user.id)
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        query = f"""
        SELECT 
            fp.process_id,
            fp.lot_id,
            fp.in_scan_weight,
            fp.flavorcore_yield_pct,
            fp.total_yield_pct,
            fp.processed_date,
            fp.status,
            fp.sample_tests,
            fp.handled_by,
            fp.supervisor_id,
            fp.supervisor_notes,
            l.crop,
            l.raw_weight,
            l.threshed_weight,
            pr.full_name as handled_by_name
        FROM flavorcore_processing fp
        LEFT JOIN lots l ON fp.lot_id = l.lot_id
        LEFT JOIN person_records pr ON fp.handled_by = pr.id
        {where_clause}
        ORDER BY fp.processed_date DESC
        LIMIT 100
        """
        
        rows = await conn.fetch(query, *params)
        await conn.close()
        
        quality_tests = []
        for row in rows:
            quality_tests.append({
                "process_id": row['process_id'],
                "lot_id": row['lot_id'],
                "crop": row['crop'],
                "in_scan_weight": float(row['in_scan_weight']) if row['in_scan_weight'] else 0,
                "flavorcore_yield_pct": float(row['flavorcore_yield_pct']) if row['flavorcore_yield_pct'] else 0,
                "total_yield_pct": float(row['total_yield_pct']) if row['total_yield_pct'] else 0,
                "processed_date": row['processed_date'].isoformat() if row['processed_date'] else None,
                "status": row['status'] or 'pending',
                "sample_tests": row['sample_tests'] or {},
                "handled_by": row['handled_by'],
                "handled_by_name": row['handled_by_name'],
                "supervisor_id": str(row['supervisor_id']) if row['supervisor_id'] else None,
                "supervisor_notes": row['supervisor_notes'],
                "raw_weight": float(row['raw_weight']) if row['raw_weight'] else 0,
                "threshed_weight": float(row['threshed_weight']) if row['threshed_weight'] else 0
            })
        
        return {
            "success": True,
            "data": quality_tests,
            "message": f"Retrieved {len(quality_tests)} quality tests successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving quality tests: {str(e)}")

@router.post("/quality-tests/enhanced")
async def create_quality_test_enhanced(
    test_data: QualityTestCreate,
    current_user = Depends(require_supervisor)
):
    """Create a new quality test record with supervisor context - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        # Check if lot exists
        lot_check = "SELECT lot_id, crop FROM lots WHERE lot_id = $1"
        lot_data = await conn.fetchrow(lot_check, test_data.lot_id)
        
        if not lot_data:
            await conn.close()
            raise HTTPException(status_code=404, detail="Lot not found")
        
        # Check if quality test already exists for this lot
        existing_test = "SELECT process_id FROM flavorcore_processing WHERE lot_id = $1"
        existing = await conn.fetchval(existing_test, test_data.lot_id)
        
        if existing:
            await conn.close()
            raise HTTPException(status_code=400, detail="Quality test already exists for this lot")
        
        query = """
        INSERT INTO flavorcore_processing (
            lot_id, 
            in_scan_weight, 
            handled_by, 
            supervisor_id, 
            sample_tests, 
            status, 
            processed_date,
            supervisor_notes
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING process_id, processed_date
        """
        
        now = datetime.now()
        row = await conn.fetchrow(
            query,
            test_data.lot_id,
            test_data.in_scan_weight,
            test_data.handled_by,
            current_user.id,
            test_data.sample_tests,
            "in_progress",
            now,
            test_data.supervisor_notes
        )
        
        await conn.close()
        
        # Send quality test completion notification
        await notification_service.notify_quality_test_completion(
            lot_id=test_data.lot_id,
            crop=lot_data['crop'],
            supervisor_name=current_user.full_name or current_user.staff_id,
            quality_score=None  # You can calculate this from sample_tests if needed
        )
        
        return {
            "success": True,
            "data": {
                "process_id": row['process_id'],
                "processed_date": row['processed_date'].isoformat(),
                "supervisor_id": str(current_user.id),
                "message": "Quality test created successfully"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating quality test: {str(e)}")

@router.put("/quality-tests/{process_id}")
async def update_quality_test(
    process_id: str,
    test_update: QualityTestUpdate,
    current_user = Depends(require_supervisor)
):
    """Update a quality test record - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        # Check if test exists and belongs to supervisor
        check_query = """
        SELECT process_id, supervisor_id, lot_id
        FROM flavorcore_processing 
        WHERE process_id = $1
        """
        existing = await conn.fetchrow(check_query, process_id)
        
        if not existing:
            await conn.close()
            raise HTTPException(status_code=404, detail="Quality test not found")
        
        # Verify supervisor has access (either created by them or assigned to them)
        if (existing['supervisor_id'] and 
            str(existing['supervisor_id']) != str(current_user.id)):
            await conn.close()
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to update this quality test"
            )
        
        # Build dynamic update query
        update_fields = []
        values = []
        param_count = 1
        
        if test_update.in_scan_weight is not None:
            update_fields.append(f"in_scan_weight = ${param_count}")
            values.append(test_update.in_scan_weight)
            param_count += 1
        
        if test_update.sample_tests is not None:
            update_fields.append(f"sample_tests = ${param_count}")
            values.append(test_update.sample_tests)
            param_count += 1
        
        if test_update.flavorcore_yield_pct is not None:
            update_fields.append(f"flavorcore_yield_pct = ${param_count}")
            values.append(test_update.flavorcore_yield_pct)
            param_count += 1
        
        if test_update.total_yield_pct is not None:
            update_fields.append(f"total_yield_pct = ${param_count}")
            values.append(test_update.total_yield_pct)
            param_count += 1
        
        if test_update.status is not None:
            update_fields.append(f"status = ${param_count}")
            values.append(test_update.status)
            param_count += 1
        
        if test_update.supervisor_notes is not None:
            update_fields.append(f"supervisor_notes = ${param_count}")
            values.append(test_update.supervisor_notes)
            param_count += 1
        
        if not update_fields:
            await conn.close()
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add updated timestamp
        update_fields.append(f"updated_at = ${param_count}")
        values.append(datetime.now())
        param_count += 1
        
        # Add process_id for WHERE clause
        values.append(process_id)
        
        query = f"""
        UPDATE flavorcore_processing 
        SET {', '.join(update_fields)}
        WHERE process_id = ${param_count}
        RETURNING process_id, status, supervisor_notes, updated_at
        """
        
        row = await conn.fetchrow(query, *values)
        await conn.close()
        
        # Send notification if status changed to completed
        if test_update.status == 'completed':
            lot_data = await get_lot_details_by_process(conn, process_id)
            if lot_data:
                await notification_service.notify_quality_test_completion(
                    lot_id=existing['lot_id'],
                    crop=lot_data.get('crop', 'Unknown'),
                    supervisor_name=current_user.full_name or current_user.staff_id,
                    quality_score=test_update.flavorcore_yield_pct
                )
        
        return {
            "success": True,
            "data": {
                "process_id": row['process_id'],
                "status": row['status'],
                "supervisor_notes": row['supervisor_notes'],
                "updated_at": row['updated_at'].isoformat()
            },
            "message": "Quality test updated successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating quality test: {str(e)}")

async def get_lot_details_by_process(conn, process_id: str):
    """Get lot details by process ID"""
    query = """
    SELECT l.crop FROM lots l
    JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
    WHERE fp.process_id = $1
    """
    return await conn.fetchrow(query, process_id)

@router.get("/workers/available")
async def get_available_workers(current_user = Depends(require_supervisor)):
    """Get workers available for assignment today - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            pr.id,
            pr.staff_id,
            pr.full_name,
            pr.person_type,
            pr.designation,
            al.timestamp as last_check_in,
            al.status as current_status
        FROM person_records pr
        LEFT JOIN attendance_logs al ON (
            al.person_id = pr.id 
            AND al.timestamp >= CURRENT_DATE 
            AND al.timestamp = (
                SELECT MAX(timestamp) 
                FROM attendance_logs 
                WHERE person_id = pr.id 
                AND timestamp >= CURRENT_DATE
            )
        )
        WHERE pr.person_type IN ('harvesting', 'staff')
        AND pr.status = 'active'
        ORDER BY pr.full_name
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        available_workers = []
        for row in rows:
            available_workers.append({
                "id": str(row['id']),
                "staff_id": row['staff_id'],
                "full_name": row['full_name'],
                "person_type": row['person_type'],
                "designation": row['designation'],
                "current_status": row['current_status'] or 'not_checked_in',
                "last_check_in": row['last_check_in'].isoformat() if row['last_check_in'] else None,
                "available_for_assignment": row['current_status'] == 'present' and not row['current_status'] == 'checked_out'
            })
        
        return {
            "success": True,
            "data": available_workers,
            "message": f"Retrieved {len(available_workers)} workers successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving available workers: {str(e)}")

@router.post("/workers/assign/enhanced")
async def assign_worker_to_job(
    assignment: WorkerAssignmentCreate,
    current_user = Depends(require_supervisor)
):
    """Assign a worker to specific jobs/tasks - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        # Check if worker exists and is active
        worker_check = """
        SELECT id, full_name, status 
        FROM person_records 
        WHERE id = $1 AND status = 'active'
        """
        worker = await conn.fetchrow(worker_check, uuid.UUID(assignment.person_id))
        
        if not worker:
            await conn.close()
            raise HTTPException(status_code=404, detail="Worker not found or inactive")
        
        # Create assignment record (using attendance_logs or a dedicated assignments table)
        query = """
        INSERT INTO attendance_logs (
            person_id, 
            method, 
            location, 
            status, 
            timestamp,
            assigned_jobs,
            assigned_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, timestamp
        """
        
        now = datetime.now()
        assignment_id = await conn.fetchval(
            query,
            uuid.UUID(assignment.person_id),
            "supervisor_assignment",
            assignment.location,
            "assigned",
            now,
            assignment.assigned_jobs,
            current_user.id
        )
        
        await conn.close()
        
        # Send assignment notification to worker
        await notification_service.notify_worker_assignment(
            worker_id=assignment.person_id,
            worker_name=worker['full_name'],
            assigned_jobs=assignment.assigned_jobs or ["General duties"],
            assigned_by=current_user.full_name or current_user.staff_id
        )
        
        return {
            "success": True,
            "data": {
                "assignment_id": str(assignment_id),
                "worker_id": assignment.person_id,
                "worker_name": worker['full_name'],
                "assigned_jobs": assignment.assigned_jobs,
                "assigned_at": now.isoformat(),
                "assigned_by": current_user.staff_id
            },
            "message": f"Worker {worker['full_name']} assigned successfully"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worker ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning worker: {str(e)}")

@router.post("/submit-packed-products/enhanced")
async def submit_packed_products_enhanced(
    submission: PackedProductSubmit,
    current_user = Depends(require_supervisor)
):
    """Submit packed products with enhanced validation - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        # Check if lot exists and has quality testing
        lot_check = """
        SELECT l.lot_id, l.crop, fp.process_id, fp.status as processing_status
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        WHERE l.lot_id = $1
        """
        lot_data = await conn.fetchrow(lot_check, submission.lot_id)
        
        if not lot_data:
            await conn.close()
            raise HTTPException(status_code=404, detail="Lot not found")
        
        if not lot_data['process_id']:
            await conn.close()
            raise HTTPException(
                status_code=400, 
                detail="Quality testing required before product submission"
            )
        
        if lot_data['processing_status'] != 'completed':
            await conn.close()
            raise HTTPException(
                status_code=400, 
                detail="Quality testing must be completed before product submission"
            )
        
        # Update the processing record with submission details
        query = """
        UPDATE flavorcore_processing 
        SET 
            status = 'submitted', 
            submitted_at = $1,
            supervisor_id = $2,
            packed_quantity = $3,
            packaging_type = $4,
            quality_grade = $5,
            supervisor_notes = $6,
            updated_at = $7
        WHERE lot_id = $8
        RETURNING process_id, submitted_at
        """
        
        now = datetime.now()
        row = await conn.fetchrow(
            query,
            now,
            current_user.id,
            submission.quantity_packed,
            submission.packaging_type,
            submission.quality_grade,
            submission.supervisor_notes,
            now,
            submission.lot_id
        )
        
        await conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Processing record not found for this lot")
        
        submission_data = {
            "submission_id": f"SUB{now.strftime('%Y%m%d%H%M%S')}",
            "process_id": str(row['process_id']),
            "lot_id": submission.lot_id,
            "quantity_packed": submission.quantity_packed,
            "packaging_type": submission.packaging_type,
            "quality_grade": submission.quality_grade,
            "supervisor_id": str(current_user.id),
            "supervisor_staff_id": current_user.staff_id,
            "submission_date": row['submitted_at'].isoformat(),
            "status": "submitted",
            "notes": submission.supervisor_notes
        }
        
        # Send product submission notification
        await notification_service.notify_product_submission(
            lot_id=submission.lot_id,
            quantity_packed=submission.quantity_packed,
            packaging_type=submission.packaging_type,
            supervisor_name=current_user.full_name or current_user.staff_id
        )
        
        return {
            "success": True,
            "data": submission_data,
            "message": "Packed products submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting packed products: {str(e)}")

@router.get("/reports/daily-production")
async def get_daily_production_report(
    report_date: date = Query(..., description="Report date"),
    current_user = Depends(require_supervisor)
):
    """Get daily production report for supervisor - NEW FEATURE"""
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            l.lot_id,
            l.crop,
            l.raw_weight,
            l.threshed_weight,
            l.estate_yield_pct,
            l.workers_involved,
            fp.status as processing_status,
            fp.in_scan_weight,
            fp.flavorcore_yield_pct,
            fp.total_yield_pct,
            fp.packed_quantity,
            fp.quality_grade
        FROM lots l
        LEFT JOIN flavorcore_processing fp ON l.lot_id = fp.lot_id
        WHERE l.date_harvested = $1
        ORDER BY l.crop, l.lot_id
        """
        
        rows = await conn.fetch(query, report_date)
        await conn.close()
        
        report_data = {
            "report_date": report_date.isoformat(),
            "supervisor": current_user.staff_id,
            "generated_at": datetime.now().isoformat(),
            "lots": [],
            "summary": {
                "total_lots": len(rows),
                "total_raw_weight": 0,
                "total_threshed_weight": 0,
                "total_packed": 0,
                "crops": {}
            }
        }
        
        for row in rows:
            lot_data = {
                "lot_id": row['lot_id'],
                "crop": row['crop'],
                "raw_weight": float(row['raw_weight']) if row['raw_weight'] else 0,
                "threshed_weight": float(row['threshed_weight']) if row['threshed_weight'] else 0,
                "estate_yield_pct": float(row['estate_yield_pct']) if row['estate_yield_pct'] else 0,
                "workers_count": len(row['workers_involved']) if row['workers_involved'] else 0,
                "processing_status": row['processing_status'],
                "in_scan_weight": float(row['in_scan_weight']) if row['in_scan_weight'] else 0,
                "flavorcore_yield_pct": float(row['flavorcore_yield_pct']) if row['flavorcore_yield_pct'] else 0,
                "total_yield_pct": float(row['total_yield_pct']) if row['total_yield_pct'] else 0,
                "packed_quantity": float(row['packed_quantity']) if row['packed_quantity'] else 0,
                "quality_grade": row['quality_grade']
            }
            
            report_data["lots"].append(lot_data)
            
            # Update summary
            report_data["summary"]["total_raw_weight"] += lot_data["raw_weight"]
            report_data["summary"]["total_threshed_weight"] += lot_data["threshed_weight"]
            report_data["summary"]["total_packed"] += lot_data["packed_quantity"]
            
            # Update crop summary
            crop = lot_data["crop"]
            if crop not in report_data["summary"]["crops"]:
                report_data["summary"]["crops"][crop] = {
                    "lots": 0,
                    "raw_weight": 0,
                    "threshed_weight": 0
                }
            report_data["summary"]["crops"][crop]["lots"] += 1
            report_data["summary"]["crops"][crop]["raw_weight"] += lot_data["raw_weight"]
            report_data["summary"]["crops"][crop]["threshed_weight"] += lot_data["threshed_weight"]
        
        return {
            "success": True,
            "data": report_data,
            "message": f"Daily production report for {report_date} generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating production report: {str(e)}")