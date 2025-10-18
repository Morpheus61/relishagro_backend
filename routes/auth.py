# routes/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import uuid
from supabase import create_client, Client
import os
from pydantic import BaseModel
from database import get_db_connection
import asyncpg

router = APIRouter()
security = HTTPBearer()

# Supabase client initialization
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    staff_id: Optional[str] = None
    full_name: Optional[str] = None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserProfile:
    """Get current authenticated user from Supabase"""
    try:
        # Verify the JWT token with Supabase
        user_data = supabase.auth.get_user(credentials.credentials)
        
        if not user_data.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get additional user profile from person_records
        user_profile = await get_user_profile(user_data.user.id)
        
        return UserProfile(
            id=user_data.user.id,
            email=user_data.user.email,
            role=user_profile.get("role", "staff"),
            staff_id=user_profile.get("staff_id"),
            full_name=user_profile.get("full_name")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile from person_records table"""
    try:
        conn = await get_db_connection()
        query = """
        SELECT 
            pr.person_type as role,
            pr.staff_id,
            pr.full_name
        FROM person_records pr
        WHERE pr.system_account_id = $1
        """
        profile = await conn.fetchrow(query, uuid.UUID(user_id))
        await conn.close()
        
        if profile:
            return {
                "role": profile['role'],
                "staff_id": profile['staff_id'],
                "full_name": profile['full_name']
            }
        return {"role": "staff"}
        
    except Exception:
        return {"role": "staff"}

# Role-based access control dependencies
async def require_admin(user: UserProfile = Depends(get_current_user)):
    if user.role not in ["admin", "harvestflow_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

async def require_supervisor(user: UserProfile = Depends(get_current_user)):
    allowed_roles = ["supervisor", "flavorcore_supervisor", "admin", "flavorcore_manager"]
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor privileges required"
        )
    return user

async def require_manager(user: UserProfile = Depends(get_current_user)):
    allowed_roles = ["admin", "harvestflow_manager", "flavorcore_manager", "flavorcore_supervisor"]
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager privileges required"
        )
    return user

@router.get("/me")
async def get_current_user_profile(current_user: UserProfile = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "staff_id": current_user.staff_id,
            "full_name": current_user.full_name
        },
        "message": "User profile retrieved successfully"
    }