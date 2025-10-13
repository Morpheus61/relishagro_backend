"""
RelishAgro Backend - Workers Routes (FIXED)
Complete worker management with proper trailing slash handling
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models.person_record import PersonRecord
from typing import List, Optional
from pydantic import BaseModel
import logging

# Router
router = APIRouter()

# Response Models
class WorkerSummary(BaseModel):
    staff_id: str
    first_name: str
    last_name: str
    role: str
    is_active: bool

class WorkersResponse(BaseModel):
    workers: List[WorkerSummary]
    total_count: int

# Utility Functions
def get_role_from_staff_id(staff_id: str) -> str:
    """Extract role from staff_id prefix"""
    if staff_id.startswith("Admin-"):
        return "Admin"
    elif staff_id.startswith("HF-"):
        return "HarvestFlow"
    elif staff_id.startswith("FC-"):
        return "FlavorCore"
    elif staff_id.startswith("SUP-"):
        return "Supervisor"
    else:
        return "Worker"

# Routes

@router.get("/", response_model=WorkersResponse)
@router.get("", response_model=WorkersResponse)  # Handle both with and without trailing slash
async def get_workers(db: Session = Depends(get_db)):
    """Get all workers from the database"""
    try:
        # Query all person records
        workers_query = db.query(PersonRecord).all()
        
        # Convert to response format
        workers_list = []
        for worker in workers_query:
            workers_list.append(WorkerSummary(
                staff_id=worker.staff_id,
                first_name=worker.first_name or "",
                last_name=worker.last_name or "",
                role=get_role_from_staff_id(worker.staff_id),
                is_active=True  # Default to active
            ))
        
        return WorkersResponse(
            workers=workers_list,
            total_count=len(workers_list)
        )
        
    except Exception as e:
        logging.error(f"Error fetching workers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve workers: {str(e)}"
        )

@router.get("/{staff_id}")
async def get_worker_by_id(staff_id: str, db: Session = Depends(get_db)):
    """Get specific worker by staff_id"""
    try:
        worker = db.query(PersonRecord).filter(PersonRecord.staff_id == staff_id).first()
        
        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with staff_id {staff_id} not found"
            )
        
        return {
            "staff_id": worker.staff_id,
            "first_name": worker.first_name,
            "last_name": worker.last_name,
            "role": get_role_from_staff_id(worker.staff_id),
            "is_active": True,
            "created_at": worker.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting worker {staff_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve worker: {str(e)}"
        )

@router.get("/role/{role}")
async def get_workers_by_role(role: str, db: Session = Depends(get_db)):
    """Get workers filtered by role"""
    try:
        # Map role to staff_id prefix
        role_prefix_map = {
            "admin": "Admin-",
            "harvestflow": "HF-",
            "flavorcore": "FC-",
            "supervisor": "SUP-"
        }
        
        prefix = role_prefix_map.get(role.lower())
        if not prefix:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}. Valid roles: admin, harvestflow, flavorcore, supervisor"
            )
        
        workers = db.query(PersonRecord).filter(
            PersonRecord.staff_id.like(f"{prefix}%")
        ).all()
        
        workers_list = []
        for worker in workers:
            workers_list.append({
                "staff_id": worker.staff_id,
                "first_name": worker.first_name,
                "last_name": worker.last_name,
                "role": get_role_from_staff_id(worker.staff_id),
                "is_active": True,
                "created_at": worker.created_at
            })
        
        return {
            "workers": workers_list,
            "total_count": len(workers_list),
            "filtered_by_role": role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting workers by role {role}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve workers by role: {str(e)}"
        )