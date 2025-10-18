# Add these imports to auth.py
import jwt
from datetime import datetime, timedelta
import secrets

# Add JWT secret key (use environment variable in production)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

# Update the login endpoint in auth.py
@router.post("/login")
async def login(login_data: LoginRequest):
    """Login with staff ID - Returns proper JWT token"""
    try:
        conn = await get_db_connection()
        
        # Find user by staff_id in person_records
        query = """
        SELECT 
            staff_id,
            first_name,
            last_name, 
            person_type as role
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
            "sub": user['staff_id'],
            "role": user['role'],
            "first_name": user['first_name'] or "",
            "last_name": user['last_name'] or "",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return LoginResponse(
            access_token=token,
            staff_id=user['staff_id'],
            role=user['role'],
            first_name=user['first_name'] or "",
            last_name=user['last_name'] or ""
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

# Add a token verification endpoint
@router.post("/verify-token")
async def verify_token(token: str = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"valid": True, "user": payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")