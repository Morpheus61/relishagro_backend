# routes/auth.py
import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import uuid
from supabase import create_client, Client
from pydantic import BaseModel
from database import get_db_connection
import asyncpg
import jwt
from datetime import datetime, timedelta
from jwt.exceptions import InvalidTokenError

router = APIRouter()
security = HTTPBearer()

# Supabase client initialization
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# JWT Configuration
JWT_SECRET = os.getenv("SECRET_KEY", "2WJa-_ZdZAAogvRDVwy3T3n826O729i_R85m4F6T2H4")
JWT_ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Login request/response models
class LoginRequest(BaseModel):
    staff_id: str

class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    staff_id: Optional[str] = None
    full_name: Optional[str] = None

@router.post("/login")
async def login(login_data: LoginRequest):
    """Login with staff ID - Returns proper JWT token in frontend-compatible format"""
    try:
        conn = await get_db_connection()
        
        # Find user by staff_id in person_records
        query = """
        SELECT 
            id,
            staff_id,
            first_name,
            last_name, 
            person_type as role,
            designation,
            contact_number
        FROM person_records 
        WHERE staff_id = $1 AND status = 'active'
        """
        
        user = await conn.fetchrow(query, login_data.staff_id)
        await conn.close()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid staff ID or user not active"
            )
        
        # Create JWT token with user data
        token_data = {
            "sub": str(user['id']),
            "staff_id": user['staff_id'],
            "role": user['role'],
            "first_name": user['first_name'] or "",
            "last_name": user['last_name'] or "",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # ✅ RETURN IN FRONTEND-COMPATIBLE FORMAT
        return {
            "success": True,
            "data": {
                "token": token,
                "user": {
                    "id": str(user['id']),
                    "staff_id": user['staff_id'],
                    "role": user['role'],
                    "first_name": user['first_name'] or "",
                    "last_name": user['last_name'] or "",
                    "full_name": f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or user['staff_id'],
                    "designation": user['designation'] or "Staff Member",
                    "department": "General",
                    "username": user['staff_id'],
                    "email": user['contact_number'] or f"{user['staff_id']}@relishagro.com"
                }
            },
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserProfile:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Get user data from token
        staff_id = payload.get("staff_id")
        role = payload.get("role")
        first_name = payload.get("first_name", "")
        last_name = payload.get("last_name", "")
        user_id = payload.get("sub")
        
        if not staff_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing staff_id"
            )
        
        return UserProfile(
            id=user_id or staff_id,
            email=f"{staff_id}@relishagro.com",
            role=role,
            staff_id=staff_id,
            full_name=f"{first_name} {last_name}".strip() or staff_id
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
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

@router.post("/verify")
async def verify_token(current_user: UserProfile = Depends(get_current_user)):
    """Verify JWT token validity"""
    return {
        "success": True,
        "valid": True,
        "user": {
            "staff_id": current_user.staff_id,
            "role": current_user.role,
            "full_name": current_user.full_name
        }
    }

@router.get("/health")
async def auth_health_check():
    """Auth service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat()
    }