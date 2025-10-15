"""
RelishAgro Backend - CORRECTED Mobile-Compatible Authentication
Staff ID only authentication with comprehensive mobile browser support
CORRECTED to work with actual database.py structure
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional
import jwt
import logging

# CORRECTED: Import from actual database structure
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

def is_mobile_browser(user_agent: str) -> bool:
    """Detect if request is from mobile browser"""
    mobile_keywords = [
        'Mobile', 'Android', 'iPhone', 'iPad', 'iPod', 
        'BlackBerry', 'Windows Phone', 'Opera Mini'
    ]
    return any(keyword in user_agent for keyword in mobile_keywords)

# MOBILE-COMPATIBLE ROUTES

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    MOBILE-COMPATIBLE Staff ID only authentication - no password required
    Enhanced with mobile browser detection and compatibility features
    """
    try:
        # Get user agent for mobile detection
        user_agent = request.headers.get("user-agent", "")
        is_mobile = is_mobile_browser(user_agent)
        
        # Log detailed request information for mobile debugging
        logging.info(f"🔐 Login attempt from {'mobile' if is_mobile else 'desktop'}")
        logging.info(f"User-Agent: {user_agent}")
        logging.info(f"Client IP: {request.client.host if request.client else 'unknown'}")
        logging.info(f"Staff ID: {login_data.staff_id}")
        
        # Query user from database
        user = db.query(PersonRecord).filter(
            PersonRecord.staff_id == login_data.staff_id
        ).first()
        
        if not user:
            logging.warning(f"❌ Login failed - Invalid staff_id: {login_data.staff_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid staff ID. User not found."
            )
        
        # Extract role from staff_id
        role = get_role_from_staff_id(user.staff_id)
        
        # Create access token with mobile-specific claims
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "sub": user.staff_id, 
            "role": role,
            "mobile": is_mobile,
            "iat": datetime.utcnow()
        }
        
        access_token = create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        logging.info(f"✅ SUCCESSFUL LOGIN - Staff: {user.staff_id}, Role: {role}, Mobile: {is_mobile}")
        
        # Create response with mobile compatibility flag
        response_data = LoginResponse(
            access_token=access_token,
            token_type="bearer",
            staff_id=user.staff_id,
            role=role,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            mobile_compatible=True
        )
        
        # Create JSON response with mobile-friendly headers
        response = JSONResponse(
            content=response_data.dict(),
            status_code=200
        )
        
        # Add mobile-specific headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ LOGIN ERROR for {login_data.staff_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

# MOBILE TEST ENDPOINT - GET method for direct browser testing
@router.get("/mobile-test")
async def mobile_auth_test(request: Request):
    """
    Mobile connectivity test endpoint - accessible via GET for browser testing
    """
    user_agent = request.headers.get("user-agent", "")
    is_mobile = is_mobile_browser(user_agent)
    
    return {
        "status": "success",
        "message": "Mobile authentication service is working",
        "mobile_detected": is_mobile,
        "user_agent": user_agent,
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints_available": {
            "login": "POST /api/auth/login",
            "user_info": "GET /api/auth/me",
            "logout": "POST /api/auth/logout",
            "health": "GET /api/auth/health"
        }
    }

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(current_user: PersonRecord = Depends(get_current_user)):
    """
    Get current authenticated user information - mobile compatible
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
        logging.info(f"🚪 User {current_user.staff_id} logged out")
        return {"message": "Logged out successfully", "mobile_compatible": True}
        
    except Exception as e:
        logging.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    """
    Health check endpoint for authentication service with mobile detection
    """
    user_agent = request.headers.get("user-agent", "")
    is_mobile = is_mobile_browser(user_agent)
    
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication_method": "staff_id_only",
        "mobile_compatible": True,
        "client_type": "mobile" if is_mobile else "desktop",
        "cors_enabled": True
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
            "last_name": current_user.last_name,
            "mobile_compatible": True
        }
        
    except Exception as e:
        logging.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

# ADDITIONAL MOBILE DEBUGGING ENDPOINTS

@router.get("/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint to inspect request headers from mobile"""
    return {
        "headers": dict(request.headers),
        "method": request.method,
        "url": str(request.url),
        "client": str(request.client) if request.client else None,
        "user_agent": request.headers.get("user-agent", "Not provided")
    }

@router.options("/login")
async def login_options():
    """Handle preflight OPTIONS request for login endpoint"""
    return JSONResponse(
        content={"message": "OPTIONS OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600"
        }
    )