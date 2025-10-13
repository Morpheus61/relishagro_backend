from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import asyncio
from datetime import datetime, date

router = APIRouter()

# Mock data for supervisor dashboard
MOCK_LOTS_DATA = [
    {
        "id": "LOT001",
        "product_type": "Tomatoes",
        "quantity": 500,
        "status": "In Progress",
        "supervisor": "John Smith",
        "start_date": "2024-01-15",
        "expected_completion": "2024-01-20"
    },
    {
        "id": "LOT002", 
        "product_type": "Peppers",
        "quantity": 300,
        "status": "Quality Check",
        "supervisor": "Jane Doe",
        "start_date": "2024-01-14",
        "expected_completion": "2024-01-19"
    }
]

MOCK_QUALITY_TESTS = [
    {
        "id": "QT001",
        "lot_id": "LOT001",
        "test_type": "Visual Inspection",
        "result": "Pass",
        "tested_by": "Alice Johnson",
        "test_date": "2024-01-16T10:30:00Z",
        "notes": "Good color and firmness"
    },
    {
        "id": "QT002",
        "lot_id": "LOT002", 
        "test_type": "Size Grading",
        "result": "Pass",
        "tested_by": "Bob Wilson",
        "test_date": "2024-01-16T14:15:00Z",
        "notes": "95% Grade A peppers"
    }
]

MOCK_WORKER_ASSIGNMENTS = [
    {
        "id": "WA001",
        "worker_name": "Maria Garcia",
        "worker_id": "W001",
        "lot_id": "LOT001",
        "task": "Sorting",
        "assigned_date": "2024-01-15",
        "status": "Active"
    },
    {
        "id": "WA002",
        "worker_name": "Carlos Rodriguez", 
        "worker_id": "W002",
        "lot_id": "LOT002",
        "task": "Packaging",
        "assigned_date": "2024-01-16",
        "status": "Active"
    }
]

@router.get("/lots")
async def get_lots():
    """Get all production lots for supervisor dashboard"""
    try:
        return {
            "success": True,
            "data": MOCK_LOTS_DATA,
            "message": "Lots retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving lots: {str(e)}")

@router.get("/lots/{lot_id}")
async def get_lot_details(lot_id: str):
    """Get detailed information about a specific lot"""
    try:
        lot = next((lot for lot in MOCK_LOTS_DATA if lot["id"] == lot_id), None)
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found")
        
        return {
            "success": True,
            "data": lot,
            "message": "Lot details retrieved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving lot details: {str(e)}")

@router.get("/quality-tests")
async def get_quality_tests():
    """Get all quality test results"""
    try:
        return {
            "success": True,
            "data": MOCK_QUALITY_TESTS,
            "message": "Quality tests retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving quality tests: {str(e)}")

@router.post("/quality-tests")
async def create_quality_test(test_data: Dict[str, Any]):
    """Create a new quality test record"""
    try:
        new_test = {
            "id": f"QT{len(MOCK_QUALITY_TESTS) + 1:03d}",
            "lot_id": test_data.get("lot_id"),
            "test_type": test_data.get("test_type"),
            "result": test_data.get("result"),
            "tested_by": test_data.get("tested_by"),
            "test_date": datetime.now().isoformat(),
            "notes": test_data.get("notes", "")
        }
        
        MOCK_QUALITY_TESTS.append(new_test)
        
        return {
            "success": True,
            "data": new_test,
            "message": "Quality test created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating quality test: {str(e)}")

@router.get("/worker-assignments")
async def get_worker_assignments():
    """Get all worker assignments for supervisor review"""
    try:
        return {
            "success": True,
            "data": MOCK_WORKER_ASSIGNMENTS,
            "message": "Worker assignments retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving worker assignments: {str(e)}")

@router.post("/worker-assignments")
async def assign_worker(assignment_data: Dict[str, Any]):
    """Assign a worker to a specific lot and task"""
    try:
        new_assignment = {
            "id": f"WA{len(MOCK_WORKER_ASSIGNMENTS) + 1:03d}",
            "worker_name": assignment_data.get("worker_name"),
            "worker_id": assignment_data.get("worker_id"),
            "lot_id": assignment_data.get("lot_id"),
            "task": assignment_data.get("task"),
            "assigned_date": date.today().isoformat(),
            "status": "Active"
        }
        
        MOCK_WORKER_ASSIGNMENTS.append(new_assignment)
        
        return {
            "success": True,
            "data": new_assignment,
            "message": "Worker assigned successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning worker: {str(e)}")

@router.post("/submit-packed-products")
async def submit_packed_products(submission_data: Dict[str, Any]):
    """Submit packed products for final processing"""
    try:
        submission = {
            "submission_id": f"SUB{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "lot_id": submission_data.get("lot_id"),
            "quantity_packed": submission_data.get("quantity_packed"),
            "supervisor_id": submission_data.get("supervisor_id"),
            "submission_date": datetime.now().isoformat(),
            "status": "Submitted",
            "notes": submission_data.get("notes", "")
        }
        
        return {
            "success": True,
            "data": submission,
            "message": "Packed products submitted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting packed products: {str(e)}")

@router.get("/rfid-scans")
async def get_rfid_scans():
    """Get recent RFID scan data"""
    try:
        mock_scans = [
            {
                "scan_id": "RFID001",
                "rfid_tag": "RF12345678",
                "worker_id": "W001",
                "worker_name": "Maria Garcia",
                "scan_time": datetime.now().isoformat(),
                "location": "Processing Area A",
                "status": "Active"
            },
            {
                "scan_id": "RFID002", 
                "rfid_tag": "RF87654321",
                "worker_id": "W002",
                "worker_name": "Carlos Rodriguez",
                "scan_time": datetime.now().isoformat(),
                "location": "Packaging Area",
                "status": "Active"
            }
        ]
        
        return {
            "success": True,
            "data": mock_scans,
            "message": "RFID scans retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving RFID scans: {str(e)}")

@router.get("/process-monitoring")
async def get_process_monitoring():
    """Get real-time process monitoring data"""
    try:
        monitoring_data = {
            "active_lots": len([lot for lot in MOCK_LOTS_DATA if lot["status"] in ["In Progress", "Quality Check"]]),
            "total_workers_active": len([w for w in MOCK_WORKER_ASSIGNMENTS if w["status"] == "Active"]), 
            "quality_tests_today": len([t for t in MOCK_QUALITY_TESTS if t["test_date"].startswith("2024-01-16")]),
            "production_efficiency": 87.5,
            "quality_pass_rate": 95.2
        }
        
        return {
            "success": True,
            "data": monitoring_data,
            "message": "Process monitoring data retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving process monitoring data: {str(e)}")