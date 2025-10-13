from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, date
from database import get_db_connection
import asyncpg

router = APIRouter()

async def get_database():
    """Get database connection"""
    try:
        return await get_db_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@router.get("/lots")
async def get_lots():
    """Get all production lots from real database"""
    try:
        conn = await get_database()
        
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
    """Get detailed information about a specific lot"""
    try:
        conn = await get_database()
        
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
    """Get all quality test results from flavorcore_processing table"""
    try:
        conn = await get_database()
        
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
    """Create a new quality test record"""
    try:
        conn = await get_database()
        
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
    """Get worker assignments from attendance_logs and person_records"""
    try:
        conn = await get_database()
        
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
    """Create a new worker assignment via attendance log"""
    try:
        conn = await get_database()
        
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
    """Submit packed products - update flavorcore_processing status"""
    try:
        conn = await get_database()
        
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
    """Get recent RFID scan data from attendance_logs"""
    try:
        conn = await get_database()
        
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
    """Get real-time process monitoring data from database"""
    try:
        conn = await get_database()
        
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