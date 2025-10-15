"""
RelishAgro Backend - Mobile-Compatible Authentication (COMPLETE FIX)
Enhanced authentication with mobile browser compatibility and debugging
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional
import jwt
import logging
import re

from database import get_db
from models.person import PersonRecord

# Security
security = HTTPBearer()

# Router
router = APIRouter()

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Request/Response Models
class LoginRequest(BaseModel):
    staff_id: str = Field(..., min_length=3, max_length=50, description="Staff ID for authentication")

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    staff_id: str
    role: str
    first_name: str
    last_name: str
    expires_in: int
    mobile_compatible: bool = True

class UserResponse(BaseModel):
    staff_id: str
    first_name: str
    last_name: str
    role: str
    is_active: bool

# Mobile Detection Utility
def is_mobile_browser(user_agent: str) -> bool:
    """Detect if request is from mobile browser"""
    mobile_patterns = [
        r'iPhone', r'iPad', r'Android', r'Windows Phone', r'BlackBerry',
        r'Mobile', r'Tablet', r'Touch', r'Opera Mini', r'Opera Mobi'
    ]
    
    for pattern in mobile_patterns:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return True
    return False

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user(token: str = Depends(security), db: Session = Depends(get_db)):
    """Get current user from JWT token"""
    try:
        payload = verify_token(token.credentials)
        staff_id = payload.get("sub")
        
        if staff_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = db.query(PersonRecord).filter(PersonRecord.staff_id == staff_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

# Routes

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Staff ID only authentication - Enhanced Mobile Compatibility
    """
    try:
        # Mobile browser detection
        user_agent = request.headers.get("user-agent", "")
        is_mobile = is_mobile_browser(user_agent)
        
        logging.info(f"🔐 Login attempt - Staff ID: {login_data.staff_id}")
        logging.info(f"📱 Mobile browser: {is_mobile}")
        logging.info(f"🌐 User Agent: {user_agent}")
        logging.info(f"🔗 Origin: {request.headers.get('origin', 'N/A')}")
        logging.info(f"🗂️ Referer: {request.headers.get('referer', 'N/A')}")
        
        # Query user from database
        user = db.query(PersonRecord).filter(
            PersonRecord.staff_id == login_data.staff_id
        ).first()
        
        if not user:
            logging.error(f"❌ User not found for staff_id: {login_data.staff_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid staff ID. User not found."
            )
        
        # Extract role from staff_id
        role = get_role_from_staff_id(user.staff_id)
        
        # Create access token with mobile-friendly settings
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.staff_id, 
                "role": role,
                "mobile": is_mobile,
                "issued_at": datetime.utcnow().isoformat()
            },
            expires_delta=access_token_expires
        )
        
        logging.info(f"✅ Login successful - Staff: {user.staff_id}, Role: {role}")
        logging.info(f"🎟️ Token generated successfully")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            staff_id=user.staff_id,
            role=role,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            mobile_compatible=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Login error for staff_id {login_data.staff_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.get("/mobile-test", status_code=status.HTTP_200_OK)
async def mobile_compatibility_test(request: Request):
    """
    Mobile browser compatibility test endpoint
    """
    try:
        user_agent = request.headers.get("user-agent", "")
        is_mobile = is_mobile_browser(user_agent)
        
        return {
            "status": "success",
            "mobile_detected": is_mobile,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "cors_headers": dict(request.headers),
            "mobile_compatibility": "enabled"
        }
        
    except Exception as e:
        logging.error(f"Mobile test error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "mobile_compatibility": "disabled"
        }

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(current_user: PersonRecord = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    try:
        return UserResponse(
            staff_id=current_user.staff_id,
            first_name=current_user.first_name or "",
            last_name=current_user.last_name or "",
            role=get_role_from_staff_id(current_user.staff_id),
            is_active=True
        )
        
    except Exception as e:
        logging.error(f"Error getting user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user information: {str(e)}"
        )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: PersonRecord = Depends(get_current_user)):
    """
    Logout current user (token-based, so client should discard token)
    """
    try:
        logging.info(f"User {current_user.staff_id} logged out")
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logging.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for authentication service
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication_method": "staff_id_only",
        "mobile_compatible": True
    }

@router.post("/verify-token")
async def verify_user_token(current_user: PersonRecord = Depends(get_current_user)):
    """
    Verify if the provided token is valid and return user info
    """
    try:
        return {
            "valid": True,
            "staff_id": current_user.staff_id,
            "role": get_role_from_staff_id(current_user.staff_id),
            "first_name": current_user.first_name,
            "last_name": current_user.last_name
        }
        
    except Exception as e:
        logging.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

@router.get("/debug-headers")
async def debug_headers(request: Request):
    """
    Debug endpoint to check request headers for mobile troubleshooting
    """
    return {
        "headers": dict(request.headers),
        "client_host": request.client.host if request.client else "unknown",
        "method": request.method,
        "url": str(request.url),
        "mobile_detected": is_mobile_browser(request.headers.get("user-agent", "")),
        "timestamp": datetime.utcnow().isoformat()
    }