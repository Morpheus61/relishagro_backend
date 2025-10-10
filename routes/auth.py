from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import PersonRecord
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    staff_id: str

class LoginResponse(BaseModel):
    authenticated: bool
    user: Optional[dict] = None
    token: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    if not request.staff_id or not request.staff_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Staff ID is required"
        )
    
    user = db.query(PersonRecord).filter(
        PersonRecord.staff_id == request.staff_id.strip()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Staff ID"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    
    role_display = {
        "admin": "Administrator",
        "harvestflow_manager": "HarvestFlow Manager",
        "flavorcore_manager": "FlavorCore Manager",
        "flavorcore_supervisor": "FlavorCore Supervisor",
        "vendor": "Vendor/Supplier",
        "driver": "Driver"
    }.get(user.person_type, user.person_type)
    
    token = user.staff_id
    
    return LoginResponse(
        authenticated=True,
        user={
            "id": str(user.id),
            "staff_id": user.staff_id,
            "full_name": user.full_name or f"{user.first_name} {user.last_name}",
            "role": user.person_type,
            "role_display": role_display,
            "designation": user.designation
        },
        token=token
    )