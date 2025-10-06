from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import PersonRecord
from typing import List
import uuid

security = HTTPBearer()

ROLE_DISPLAY_NAMES = {
    "admin": "Administrator",
    "harvestflow_manager": "HarvestFlow Manager",
    "flavorcore_manager": "FlavorCore Manager",
    "flavorcore_supervisor": "FlavorCore Supervisor",
    "vendor": "Vendor/Supplier",
    "driver": "Driver"
}

ROLE_PERMISSIONS = {
    "admin": [
        "manage_users", "manage_config", "approve_all", "view_all",
        "manage_job_types", "manage_timings", "manage_rfid"
    ],
    "harvestflow_manager": [
        "onboard_workers", "record_attendance", "assign_jobs",
        "create_lots", "dispatch_lots", "request_provisions"
    ],
    "flavorcore_manager": [
        "onboard_workers", "record_attendance", "assign_jobs",
        "approve_hf_provisions", "approve_lot_completion", "manage_shifts"
    ],
    "flavorcore_supervisor": [
        "rfid_scan", "process_lots", "log_drying", "generate_qr",
        "submit_completion"
    ],
    "vendor": [
        "view_requests", "respond_to_requests"
    ],
    "driver": [
        "view_trips", "update_location", "confirm_delivery"
    ]
}

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> PersonRecord:
    """
    Get current authenticated user from token.
    For production, implement proper JWT validation.
    """
    try:
        # Extract staff_id from token (simplified for now)
        # In production: decode JWT, verify signature, check expiry
        staff_id = credentials.credentials
        
        user = db.query(PersonRecord).filter(
            PersonRecord.staff_id == staff_id,
            PersonRecord.status == "active"
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        return user
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

def require_role(allowed_roles: List[str]):
    """
    Dependency to check if user has required role.
    Usage: require_role(["admin", "harvestflow_manager"])
    """
    async def role_checker(
        current_user: PersonRecord = Depends(get_current_user)
    ) -> PersonRecord:
        if current_user.person_type not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker

def has_permission(user: PersonRecord, permission: str) -> bool:
    """Check if user has specific permission"""
    role_perms = ROLE_PERMISSIONS.get(user.person_type, [])
    return permission in role_perms