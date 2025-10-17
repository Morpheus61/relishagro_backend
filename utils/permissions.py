from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import PersonRecord
from typing import List
import jwt

security = HTTPBearer()

# JWT Configuration (should match auth.py)
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"

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

# Role mapping: JWT role -> Database person_type
ROLE_MAPPING = {
    "Admin": "admin",
    "HarvestFlow": "harvestflow_manager",
    "FlavorCore": "flavorcore_manager",
    "Supervisor": "flavorcore_supervisor",
    "Worker": "worker",
    "Vendor": "vendor",
    "Driver": "driver"
}

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> PersonRecord:
    """
    Get current authenticated user from JWT token.
    """
    try:
        # Decode JWT token
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        staff_id = payload.get("sub")
        
        if staff_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        user = db.query(PersonRecord).filter(
            PersonRecord.staff_id == staff_id
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

def require_role(allowed_roles: List[str]):
    """
    Dependency to check if user has required role.
    Handles both capitalized JWT roles and lowercase database person_types.
    Usage: require_role(["admin", "Admin", "harvestflow_manager"])
    """
    async def role_checker(
        current_user: PersonRecord = Depends(get_current_user)
    ) -> PersonRecord:
        # Normalize allowed roles to lowercase
        normalized_allowed_roles = []
        for role in allowed_roles:
            # If role is in ROLE_MAPPING (capitalized), convert to person_type
            if role in ROLE_MAPPING:
                normalized_allowed_roles.append(ROLE_MAPPING[role])
            else:
                # Already lowercase person_type format
                normalized_allowed_roles.append(role.lower())
        
        # Check if user's person_type matches any allowed role
        if current_user.person_type not in normalized_allowed_roles:
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