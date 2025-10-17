from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models import ProvisionRequest, PersonRecord
from services import NotificationService
from utils import require_role
from typing import Optional, List
from datetime import datetime
import uuid

router = APIRouter(tags=["provisions"])
notification_service = NotificationService()

@router.post("/request")
async def create_provision_request(
    request_type: str = Form(...),
    description: str = Form(...),
    amount: float = Form(...),
    vendor: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["harvestflow_manager"]))
):
    """HarvestFlow Manager creates provision request."""
    
    provision = ProvisionRequest(
        request_type=request_type,
        description=description,
        amount=amount,
        vendor=vendor,
        requested_by=current_user.id,
        requested_date=datetime.utcnow(),
        status="pending"
    )
    
    db.add(provision)
    db.commit()
    db.refresh(provision)
    
    fc_managers = db.query(PersonRecord).filter(
        PersonRecord.person_type == "flavorcore_manager",
        PersonRecord.status == "active"
    ).all()
    
    for manager in fc_managers:
        await notification_service.notify_provision_request(
            db=db,
            recipient_id=manager.id,
            request_type=request_type,
            amount=amount,
            requester_name=current_user.full_name
        )
    
    return {
        "success": True,
        "message": "Provision request submitted",
        "request_id": str(provision.id)
    }

@router.get("/pending")
async def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["flavorcore_manager", "Admin"]))  # ✅ Changed from "admin" to "Admin"
):
    """Get pending provision requests"""
    
    query = db.query(ProvisionRequest)
    
    if current_user.person_type == "flavorcore_manager":
        query = query.filter(
            ProvisionRequest.status == "pending",
            ProvisionRequest.reviewed_by_fc_manager.is_(None)
        )
    else:
        query = query.filter(
            ProvisionRequest.status == "pending",
            ProvisionRequest.reviewed_by_fc_manager.isnot(None),
            ProvisionRequest.approved_by.is_(None)
        )
    
    requests = query.order_by(ProvisionRequest.created_at.desc()).all()
    
    return {
        "success": True,
        "count": len(requests),
        "requests": [
            {
                "id": str(req.id),
                "request_type": req.request_type,
                "description": req.description,
                "amount": float(req.amount),
                "vendor": req.vendor,
                "requested_by": str(req.requested_by),
                "status": req.status,
                "created_at": req.created_at.isoformat()
            }
            for req in requests
        ]
    }

@router.post("/review/{request_id}")
async def review_provision_request(
    request_id: str,
    approved: bool = Form(...),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["flavorcore_manager"]))
):
    """FlavorCore Manager reviews HarvestFlow provision request"""
    
    provision = db.query(ProvisionRequest).filter(
        ProvisionRequest.id == uuid.UUID(request_id)
    ).first()
    
    if not provision:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if not approved:
        provision.status = "rejected"
        db.commit()
        return {"success": True, "message": "Request rejected"}
    
    provision.reviewed_by_fc_manager = current_user.id
    provision.reviewed_by_fc_manager_at = datetime.utcnow()
    
    db.commit()
    
    admins = db.query(PersonRecord).filter(
        PersonRecord.person_type == "admin",
        PersonRecord.status == "active"
    ).all()
    
    for admin in admins:
        await notification_service.notify_provision_request(
            db=db,
            recipient_id=admin.id,
            request_type=provision.request_type,
            amount=float(provision.amount),
            requester_name="HarvestFlow (via FC Manager)"
        )
    
    return {
        "success": True,
        "message": "Request forwarded to Admin for final approval"
    }

@router.post("/approve/{request_id}")
async def approve_provision_request(
    request_id: str,
    vendor_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["Admin"]))  # ✅ Changed from "admin" to "Admin"
):
    """Admin gives final approval and assigns to vendor"""
    
    provision = db.query(ProvisionRequest).filter(
        ProvisionRequest.id == uuid.UUID(request_id)
    ).first()
    
    if not provision:
        raise HTTPException(status_code=404, detail="Request not found")
    
    provision.approved_by = current_user.id
    provision.status = "approved"
    
    if vendor_id:
        provision.vendor_id = uuid.UUID(vendor_id)
        provision.vendor_notified_at = datetime.utcnow()
        
        vendor = db.query(PersonRecord).filter(
            PersonRecord.id == uuid.UUID(vendor_id)
        ).first()
        
        if vendor:
            await notification_service.create_notification(
                db=db,
                recipient_id=vendor.id,
                notification_type="vendor_request",
                title="New Provision Order",
                message=f"Order for {provision.description} - ₹{provision.amount}",
                data={"request_id": str(provision.id)},
                send_sms=True,
                send_whatsapp=True
            )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Request approved" + (" and vendor notified" if vendor_id else "")
    }