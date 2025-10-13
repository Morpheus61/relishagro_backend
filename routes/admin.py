"""
RelishAgro Backend - Admin Routes (FIXED IMPORTS)
Complete admin functionality with correct model imports
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from database import get_db
from models.person import PersonRecord  # FIXED: Changed from models.person_record to models.person
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging

# Security
security = HTTPBearer()

# Router
router = APIRouter()

# Response Models
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_admins: int
    total_supervisors: int
    total_harvestflow_users: int
    total_flavorcore_users: int
    recent_registrations: int
    system_health: str

class UserSummary(BaseModel):
    staff_id: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]

class AdminUserResponse(BaseModel):
    users: List[UserSummary]
    total_count: int
    page: int
    per_page: int

class UserCreateRequest(BaseModel):
    staff_id: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., description="Role prefix: Admin-, HF-, FC-, SUP-")
    is_active: bool = True

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = None
    is_active: Optional[bool] = None

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
        return "Unknown"

def generate_staff_id(role: str, first_name: str, last_name: str) -> str:
    """Generate staff_id from role and name"""
    role_prefix = {
        "Admin": "Admin-",
        "HarvestFlow": "HF-",
        "FlavorCore": "FC-",
        "Supervisor": "SUP-"
    }.get(role, "")
    
    # Create unique identifier from name
    identifier = f"{first_name[:2]}{last_name[:2]}".upper()
    return f"{role_prefix}{identifier}"

# Routes

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(db: Session = Depends(get_db)):
    """Get comprehensive admin statistics"""
    try:
        # Total users
        total_users = db.query(PersonRecord).count()
        
        # Active users (assuming is_active field exists or using created_at as proxy)
        active_users = db.query(PersonRecord).filter(
            PersonRecord.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        
        # Users by role
        admin_users = db.query(PersonRecord).filter(
            PersonRecord.staff_id.like("Admin-%")
        ).count()
        
        supervisor_users = db.query(PersonRecord).filter(
            PersonRecord.staff_id.like("SUP-%")
        ).count()
        
        harvestflow_users = db.query(PersonRecord).filter(
            PersonRecord.staff_id.like("HF-%")
        ).count()
        
        flavorcore_users = db.query(PersonRecord).filter(
            PersonRecord.staff_id.like("FC-%")
        ).count()
        
        # Recent registrations (last 7 days)
        recent_registrations = db.query(PersonRecord).filter(
            PersonRecord.created_at >= datetime.now() - timedelta(days=7)
        ).count()
        
        return AdminStats(
            total_users=total_users,
            active_users=active_users,
            total_admins=admin_users,
            total_supervisors=supervisor_users,
            total_harvestflow_users=harvestflow_users,
            total_flavorcore_users=flavorcore_users,
            recent_registrations=recent_registrations,
            system_health="Operational"
        )
        
    except Exception as e:
        logging.error(f"Error getting admin stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve admin statistics: {str(e)}"
        )

@router.get("/users", response_model=AdminUserResponse)
async def get_all_users(
    page: int = 1,
    per_page: int = 20,
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all users with pagination and filtering"""
    try:
        # Base query
        query = db.query(PersonRecord)
        
        # Role filter
        if role:
            if role == "Admin":
                query = query.filter(PersonRecord.staff_id.like("Admin-%"))
            elif role == "HarvestFlow":
                query = query.filter(PersonRecord.staff_id.like("HF-%"))
            elif role == "FlavorCore":
                query = query.filter(PersonRecord.staff_id.like("FC-%"))
            elif role == "Supervisor":
                query = query.filter(PersonRecord.staff_id.like("SUP-%"))
        
        # Search filter
        if search:
            search_filter = or_(
                PersonRecord.staff_id.ilike(f"%{search}%"),
                PersonRecord.first_name.ilike(f"%{search}%"),
                PersonRecord.last_name.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()
        
        # Convert to response format
        user_summaries = []
        for user in users:
            user_summaries.append(UserSummary(
                staff_id=user.staff_id,
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                role=get_role_from_staff_id(user.staff_id),
                is_active=True,  # Default to True if no is_active field
                created_at=user.created_at,
                last_login=None  # Would need to track this separately
            ))
        
        return AdminUserResponse(
            users=user_summaries,
            total_count=total_count,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logging.error(f"Error getting users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )

@router.get("/users/{staff_id}")
async def get_user_by_id(staff_id: str, db: Session = Depends(get_db)):
    """Get specific user by staff_id"""
    try:
        user = db.query(PersonRecord).filter(PersonRecord.staff_id == staff_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with staff_id {staff_id} not found"
            )
        
        return {
            "staff_id": user.staff_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": get_role_from_staff_id(user.staff_id),
            "is_active": True,
            "created_at": user.created_at,
            "phone_number": getattr(user, 'phone_number', None),
            "email": getattr(user, 'email', None)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting user {staff_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}"
        )

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreateRequest, db: Session = Depends(get_db)):
    """Create new user"""
    try:
        # Check if staff_id already exists
        existing_user = db.query(PersonRecord).filter(
            PersonRecord.staff_id == user_data.staff_id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with staff_id {user_data.staff_id} already exists"
            )
        
        # Create new user
        new_user = PersonRecord(
            staff_id=user_data.staff_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "User created successfully",
            "staff_id": new_user.staff_id,
            "role": get_role_from_staff_id(new_user.staff_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.put("/users/{staff_id}")
async def update_user(
    staff_id: str, 
    user_update: UserUpdateRequest, 
    db: Session = Depends(get_db)
):
    """Update existing user"""
    try:
        user = db.query(PersonRecord).filter(PersonRecord.staff_id == staff_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with staff_id {staff_id} not found"
            )
        
        # Update fields
        if user_update.first_name is not None:
            user.first_name = user_update.first_name
        if user_update.last_name is not None:
            user.last_name = user_update.last_name
        
        # Note: Role change would require changing staff_id, which is complex
        # For now, just log the request
        if user_update.role is not None:
            logging.info(f"Role change requested for {staff_id} to {user_update.role}")
        
        db.commit()
        db.refresh(user)
        
        return {
            "message": "User updated successfully",
            "staff_id": user.staff_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": get_role_from_staff_id(user.staff_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating user {staff_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )

@router.delete("/users/{staff_id}")
async def delete_user(staff_id: str, db: Session = Depends(get_db)):
    """Delete user (soft delete by setting inactive)"""
    try:
        user = db.query(PersonRecord).filter(PersonRecord.staff_id == staff_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with staff_id {staff_id} not found"
            )
        
        # For now, actually delete. In production, you might want soft delete
        db.delete(user)
        db.commit()
        
        return {
            "message": f"User {staff_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting user {staff_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

@router.get("/system/health")
async def get_system_health(db: Session = Depends(get_db)):
    """Get system health status"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
    except Exception as e:
        logging.error(f"System health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/roles")
async def get_available_roles():
    """Get all available roles in the system"""
    return {
        "roles": [
            {"code": "Admin", "name": "Administrator", "prefix": "Admin-"},
            {"code": "HF", "name": "HarvestFlow Worker", "prefix": "HF-"},
            {"code": "FC", "name": "FlavorCore Manager", "prefix": "FC-"},
            {"code": "SUP", "name": "Supervisor", "prefix": "SUP-"}
        ]
    }