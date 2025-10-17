from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models import OnboardingRequest, PersonRecord
from services import NotificationService, FaceRecognitionService
from utils import require_role
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import cv2
import numpy as np

router = APIRouter(tags=["onboarding"])
notification_service = NotificationService()
face_service = FaceRecognitionService()

class OnboardingSubmission(BaseModel):
    first_name: str
    last_name: str
    mobile: str
    address: str
    role: str
    aadhaar: Optional[str] = None
    is_seasonal: bool = False

@router.post("/submit")  # ✅ FIXED: Changed from "/onboarding/submit"
async def submit_onboarding(
    first_name: str = Form(...),
    last_name: str = Form(...),
    mobile: str = Form(...),
    address: str = Form(...),
    role: str = Form(...),
    aadhaar: Optional[str] = Form(None),
    is_seasonal: bool = Form(False),
    face_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["harvestflow_manager", "flavorcore_manager"]))
):
    """
    Manager submits worker onboarding request.
    Admin must approve before worker is added to system.
    """
    
    # Process face image if provided
    face_image_path = None
    face_embedding = None
    
    if face_image:
        try:
            contents = await face_image.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is not None and face_service.available:
                # Extract embedding
                face_embedding = face_service.extract_embedding(img)
                
                # Save temporary image
                temp_id = str(uuid.uuid4())
                face_image_path = face_service.save_face_image(f"pending_{temp_id}", img)
        except Exception as e:
            print(f"Face processing error: {e}")
    
    # Create onboarding request
    onboarding = OnboardingRequest(
        first_name=first_name,
        last_name=last_name,
        mobile=mobile,
        address=address,
        role=role,
        aadhaar=aadhaar,
        face_image=face_image_path,
        submitted_by=current_user.id,
        consent_given_at=datetime.utcnow() if aadhaar else None
    )
    
    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)
    
    # Notify admin
    admins = db.query(PersonRecord).filter(
        PersonRecord.person_type == "admin",
        PersonRecord.status == "active"
    ).all()
    
    for admin in admins:
        await notification_service.create_notification(
            db=db,
            recipient_id=admin.id,
            notification_type="onboarding_approval",
            title="New Worker Onboarding Request",
            message=f"{current_user.full_name} submitted onboarding for {first_name} {last_name}",
            data={"onboarding_id": str(onboarding.id)},
            send_sms=True,
            send_whatsapp=False
        )
    
    return {
        "success": True,
        "message": "Onboarding request submitted for admin approval",
        "onboarding_id": str(onboarding.id)
    }

@router.get("/pending")
async def get_pending_onboarding(
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["admin"]))
):
    """Get all pending onboarding requests (Admin only)"""
    
    requests = db.query(OnboardingRequest).filter(
        OnboardingRequest.status == "pending"
    ).order_by(OnboardingRequest.created_at.desc()).all()
    
    return {
        "success": True,
        "count": len(requests),
        "requests": [
            {
                "id": str(req.id),
                "first_name": req.first_name,
                "last_name": req.last_name,
                "mobile": req.mobile,
                "role": req.role,
                "aadhaar": req.aadhaar,
                "submitted_by": str(req.submitted_by),
                "created_at": req.created_at.isoformat()
            }
            for req in requests
        ]
    }

@router.post("/approve/{onboarding_id}")
async def approve_onboarding(
    onboarding_id: str,
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["admin"]))
):
    """
    Admin approves onboarding request.
    Creates actual PersonRecord and generates staff_id.
    """
    
    request = db.query(OnboardingRequest).filter(
        OnboardingRequest.id == uuid.UUID(onboarding_id)
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    # Generate staff_id based on role
    role_prefix_map = {
        "field-worker": "Staff",
        "supervisor": "FlavorSup",
        "driver": "Driver",
        "manager": "Manager"
    }
    
    prefix = role_prefix_map.get(request.role, "Staff")
    
    # Get count for sequential numbering
    count = db.query(PersonRecord).filter(
        PersonRecord.staff_id.like(f"{prefix}-%")
    ).count()
    
    staff_id = f"{prefix}-{count + 1:03d}"
    
    # Determine person_type
    person_type_map = {
        "field-worker": "harvesting",
        "supervisor": "flavorcore_supervisor",
        "driver": "driver",
        "manager": "staff"
    }
    
    person_type = person_type_map.get(request.role, "staff")
    
    # Create person record
    person = PersonRecord(
        staff_id=staff_id,
        first_name=request.first_name,
        last_name=request.last_name,
        full_name=f"{request.first_name} {request.last_name}",
        contact_number=request.mobile,
        address=request.address,
        person_type=person_type,
        designation=request.role,
        status="active",
        is_seasonal_worker=False,
        employment_start_date=datetime.utcnow(),
        created_by=current_user.id
    )
    
    db.add(person)
    
    # Update onboarding request
    request.status = "approved"
    request.approved_by = current_user.id
    request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(person)
    
    # Notify submitter
    await notification_service.create_notification(
        db=db,
        recipient_id=request.submitted_by,
        notification_type="onboarding_approval",
        title="Onboarding Approved",
        message=f"Worker {person.full_name} approved. Staff ID: {staff_id}",
        data={"person_id": str(person.id), "staff_id": staff_id},
        send_sms=True,
        send_whatsapp=False
    )
    
    return {
        "success": True,
        "message": "Onboarding approved",
        "person_id": str(person.id),
        "staff_id": staff_id
    }

@router.delete("/reject/{onboarding_id}")
async def reject_onboarding(
    onboarding_id: str,
    reason: str = Form(...),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["admin"]))
):
    """Admin rejects onboarding request"""
    
    request = db.query(OnboardingRequest).filter(
        OnboardingRequest.id == uuid.UUID(onboarding_id)
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request.status = "rejected"
    request.approved_by = current_user.id
    request.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Onboarding rejected"
    }