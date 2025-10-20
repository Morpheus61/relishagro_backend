# routes/onboarding.py
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import base64
import json
from database import get_db_connection
import asyncpg
from pydantic import BaseModel
from routes.auth import get_current_user, require_admin  # require_manager is not used anymore
from services.notification_service import notification_service

router = APIRouter()

# --- New dependency: allow Admin or Manager roles ---
async def require_manager_or_admin(current_user=Depends(get_current_user)):
    allowed_types = ["admin", "harvestflow_manager", "flavorcore_manager"]
    if current_user.person_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Admins or Managers can view pending onboarding requests."
        )
    return current_user


class OnboardingRequestCreate(BaseModel):
    first_name: str
    last_name: str
    mobile: Optional[str] = None
    address: Optional[str] = None
    role: str
    aadhaar: Optional[str] = None
    entity_type: str = "staff"  # staff, supplier, vendor

class SupplierOnboardingData(BaseModel):
    firm_name: str
    gst_number: str
    category: str
    contact_person: str
    address: str
    services: List[str]

@router.post("/requests")
async def create_onboarding_request(
    first_name: str = Form(...),
    last_name: str = Form(...),
    mobile: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    role: str = Form(...),
    aadhaar: Optional[str] = Form(None),
    entity_type: str = Form("staff"),
    face_image: Optional[UploadFile] = File(None),
    aadhaar_document: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user)
):
    """Create a new onboarding request with file uploads"""
    try:
        conn = await get_db_connection()
        
        # Handle file uploads
        face_image_data = None
        aadhaar_data = None
        
        if face_image:
            if not face_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Face image must be an image file")
            face_image_data = await face_image.read()
        
        if aadhaar_document:
            aadhaar_data = await aadhaar_document.read()
        
        # For suppliers/vendors, create onboarding_pending record
        if entity_type in ['supplier', 'vendor']:
            result = await create_supplier_vendor_onboarding(
                conn, first_name, last_name, mobile, address, role, aadhaar,
                face_image_data, aadhaar_data, entity_type, current_user
            )
            
            # Send notification for supplier/vendor onboarding
            await notification_service.notify_supplier_onboarding(
                request_id=result["data"]["request_id"],
                supplier_name=f"{first_name} {last_name}",
                firm_name="Unknown"  # You might want to capture this in your form
            )
            
            return result
        else:
            # For staff, create onboarding_requests record
            result = await create_staff_onboarding(
                conn, first_name, last_name, mobile, address, role, aadhaar,
                face_image_data, aadhaar_data, current_user
            )
            
            # Send notification for staff onboarding
            await notification_service.notify_new_onboarding_request(
                request_id=result["data"]["request_id"],
                request_type="staff",
                person_name=f"{first_name} {last_name}",
                submitted_by=current_user.full_name or current_user.staff_id
            )
            
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating onboarding request: {str(e)}")

async def create_staff_onboarding(conn, first_name, last_name, mobile, address, role, aadhaar, face_image_data, aadhaar_data, current_user):
    """Create staff onboarding request"""
    query = """
    INSERT INTO onboarding_requests (
        first_name, last_name, mobile, address, role, aadhaar,
        face_image, fingerprint_data, status, submitted_by, created_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    RETURNING id, created_at
    """
    
    now = datetime.now()
    row = await conn.fetchrow(
        query,
        first_name,
        last_name,
        mobile,
        address,
        role,
        aadhaar,
        base64.b64encode(face_image_data).decode() if face_image_data else None,
        None,  # fingerprint data would go here
        'pending',
        uuid.UUID(current_user.id),
        now
    )
    
    await conn.close()
    
    return {
        "success": True,
        "data": {
            "request_id": str(row['id']),
            "type": "staff",
            "submitted_at": row['created_at'].isoformat()
        },
        "message": "Staff onboarding request submitted successfully"
    }

async def create_supplier_vendor_onboarding(conn, first_name, last_name, mobile, address, role, aadhaar, face_image_data, aadhaar_data, entity_type, current_user):
    """Create supplier/vendor onboarding request"""
    onboarding_data = {
        "personal_info": {
            "first_name": first_name,
            "last_name": last_name,
            "mobile": mobile,
            "address": address,
            "aadhaar": aadhaar
        },
        "entity_type": entity_type,
        "role": role,
        "documents": {
            "face_image": base64.b64encode(face_image_data).decode() if face_image_data else None,
            "aadhaar_document": base64.b64encode(aadhaar_data).decode() if aadhaar_data else None
        }
    }
    
    query = """
    INSERT INTO onboarding_pending (
        entity_type, data, submitted_by, status, submitted_at, approval_checklist
    ) VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING id, submitted_at
    """
    
    now = datetime.now()
    approval_checklist = {
        "documents_verified": False,
        "background_check": False,
        "gst_verified": False if entity_type in ['supplier', 'vendor'] else None,
        "quality_certificates": False if entity_type in ['supplier', 'vendor'] else None
    }
    
    row = await conn.fetchrow(
        query,
        entity_type,
        json.dumps(onboarding_data),
        uuid.UUID(current_user.id),
        'pending',
        now,
        json.dumps(approval_checklist)
    )
    
    await conn.close()
    
    return {
        "success": True,
        "data": {
            "request_id": str(row['id']),
            "type": entity_type,
            "submitted_at": row['submitted_at'].isoformat()
        },
        "message": f"{entity_type.title()} onboarding request submitted successfully"
    }

@router.get("/pending")
async def get_pending_onboarding(
    entity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user = Depends(require_manager_or_admin)  # ✅ FIXED: Now allows Admins
):
    """Get all pending onboarding requests"""
    try:
        conn = await get_db_connection()
        
        where_conditions = []
        params = []
        param_count = 1
        
        if entity_type:
            where_conditions.append(f"entity_type = ${param_count}")
            params.append(entity_type)
            param_count += 1
        
        if status:
            where_conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        # Get onboarding_pending records
        pending_query = f"""
        SELECT 
            id, entity_type, data, status, submitted_at, reviewed_at,
            submitted_by, reviewed_by, remarks, approval_checklist
        FROM onboarding_pending
        {where_clause}
        ORDER BY submitted_at DESC
        """
        
        pending_rows = await conn.fetch(pending_query, *params)
        
        # Get onboarding_requests records
        requests_query = """
        SELECT 
            id, first_name, last_name, mobile, role, status,
            submitted_by, approved_by, created_at
        FROM onboarding_requests
        WHERE status = 'pending'
        ORDER BY created_at DESC
        """
        
        request_rows = await conn.fetch(requests_query)
        
        await conn.close()
        
        # Combine results
        all_requests = []
        
        for row in pending_rows:
            data = json.loads(row['data']) if row['data'] else {}
            all_requests.append({
                "id": str(row['id']),
                "type": "entity",
                "entity_type": row['entity_type'],
                "name": f"{data.get('personal_info', {}).get('first_name', '')} {data.get('personal_info', {}).get('last_name', '')}".strip(),
                "role": data.get('role'),
                "status": row['status'],
                "submitted_at": row['submitted_at'].isoformat() if row['submitted_at'] else None,
                "reviewed_at": row['reviewed_at'].isoformat() if row['reviewed_at'] else None,
                "approval_checklist": json.loads(row['approval_checklist']) if row['approval_checklist'] else {}
            })
        
        for row in request_rows:
            all_requests.append({
                "id": str(row['id']),
                "type": "staff",
                "entity_type": "staff",
                "name": f"{row['first_name']} {row['last_name']}",
                "role": row['role'],
                "status": row['status'],
                "submitted_at": row['created_at'].isoformat() if row['created_at'] else None,
                "mobile": row['mobile']
            })
        
        return {
            "success": True,
            "data": all_requests,
            "message": f"Retrieved {len(all_requests)} pending onboarding requests"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pending onboarding: {str(e)}")

@router.post("/{request_id}/approve")
async def approve_onboarding_request(
    request_id: str,
    entity_type: str = Query(..., description="staff or entity"),
    current_user = Depends(require_admin)
):
    """Approve an onboarding request"""
    try:
        conn = await get_db_connection()
        
        if entity_type == "staff":
            result = await approve_staff_onboarding(conn, request_id, current_user)
            
            # Send approval notification
            await notification_service.notify_onboarding_approved(
                person_id=result["data"]["person_id"],
                person_name=await get_person_name(conn, result["data"]["person_id"]),
                staff_id=result["data"]["staff_id"],
                approved_by=current_user.full_name or current_user.staff_id
            )
            
            return result
        else:
            result = await approve_entity_onboarding(conn, request_id, current_user)
            
            # Send approval notification for entity
            await notification_service.notify_onboarding_approved(
                person_id=result["data"]["person_id"],
                person_name=await get_person_name(conn, result["data"]["person_id"]),
                staff_id=result["data"]["staff_id"],
                approved_by=current_user.full_name or current_user.staff_id
            )
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving onboarding request: {str(e)}")

async def get_person_name(conn, person_id: str) -> str:
    """Get person name by ID"""
    query = "SELECT first_name, last_name FROM person_records WHERE id = $1"
    row = await conn.fetchrow(query, uuid.UUID(person_id))
    if row:
        return f"{row['first_name']} {row['last_name']}"
    return "Unknown"

async def approve_staff_onboarding(conn, request_id, current_user):
    """Approve staff onboarding and create person record"""
    # Get the onboarding request
    request_query = """
    SELECT first_name, last_name, mobile, address, role, aadhaar
    FROM onboarding_requests 
    WHERE id = $1 AND status = 'pending'
    """
    
    request_data = await conn.fetchrow(request_query, uuid.UUID(request_id))
    if not request_data:
        await conn.close()
        raise HTTPException(status_code=404, detail="Pending staff onboarding request not found")
    
    # Generate staff ID and create person record
    staff_id = await generate_staff_id(conn, 'staff')
    
    person_query = """
    INSERT INTO person_records (
        first_name, last_name, contact_number, address,
        person_type, designation, status, staff_id,
        employment_start_date, created_by, created_at, updated_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
    RETURNING id
    """
    
    now = datetime.now()
    person_id = await conn.fetchval(
        person_query,
        request_data['first_name'],
        request_data['last_name'],
        request_data['mobile'],
        request_data['address'],
        'staff',
        request_data['role'],
        'active',
        staff_id,
        now.date(),
        uuid.UUID(current_user.id),
        now,
        now
    )
    
    # Update onboarding request status
    update_query = """
    UPDATE onboarding_requests 
    SET status = 'approved', approved_by = $1, updated_at = $2
    WHERE id = $3
    """
    
    await conn.execute(update_query, uuid.UUID(current_user.id), now, uuid.UUID(request_id))
    await conn.close()
    
    return {
        "success": True,
        "data": {
            "person_id": str(person_id),
            "staff_id": staff_id,
            "onboarding_request_id": request_id
        },
        "message": "Staff onboarding approved and person record created successfully"
    }

async def approve_entity_onboarding(conn, request_id, current_user):
    """Approve supplier/vendor onboarding and create person record"""
    # Get the onboarding pending record
    pending_query = """
    SELECT entity_type, data, approval_checklist
    FROM onboarding_pending 
    WHERE id = $1 AND status = 'pending'
    """
    
    pending_data = await conn.fetchrow(pending_query, uuid.UUID(request_id))
    if not pending_data:
        await conn.close()
        raise HTTPException(status_code=404, detail="Pending entity onboarding request not found")
    
    data = json.loads(pending_data['data'])
    personal_info = data.get('personal_info', {})
    
    # Create person record for supplier/vendor
    staff_id = await generate_staff_id(conn, pending_data['entity_type'])
    
    person_query = """
    INSERT INTO person_records (
        first_name, last_name, contact_number, address,
        person_type, firm_name, status, staff_id,
        created_by, created_at, updated_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    RETURNING id
    """
    
    now = datetime.now()
    person_id = await conn.fetchval(
        person_query,
        personal_info.get('first_name'),
        personal_info.get('last_name'),
        personal_info.get('mobile'),
        personal_info.get('address'),
        pending_data['entity_type'],
        data.get('firm_name', ''),
        'active',
        staff_id,
        uuid.UUID(current_user.id),
        now,
        now
    )
    
    # Update onboarding pending status
    update_query = """
    UPDATE onboarding_pending 
    SET status = 'approved', reviewed_by = $1, reviewed_at = $2
    WHERE id = $3
    """
    
    await conn.execute(update_query, uuid.UUID(current_user.id), now, uuid.UUID(request_id))
    await conn.close()
    
    return {
        "success": True,
        "data": {
            "person_id": str(person_id),
            "staff_id": staff_id,
            "entity_type": pending_data['entity_type'],
            "onboarding_request_id": request_id
        },
        "message": f"{pending_data['entity_type'].title()} onboarding approved successfully"
    }

async def generate_staff_id(conn, person_type: str) -> str:
    """Generate unique staff ID based on person type"""
    prefix_map = {
        'admin': 'ADM',
        'harvestflow_manager': 'HFM',
        'flavorcore_manager': 'FCM', 
        'flavorcore_supervisor': 'FCS',
        'supervisor': 'SUP',
        'harvesting': 'HRV',
        'staff': 'STF',
        'supplier': 'SUP',
        'vendor': 'VND'
    }
    
    prefix = prefix_map.get(person_type, 'EMP')
    timestamp = datetime.now().strftime("%y%m%d")
    
    # Find the next sequence number for this prefix and date
    sequence_query = """
    SELECT COUNT(*) as count 
    FROM person_records 
    WHERE staff_id LIKE $1
    """
    pattern = f"{prefix}-{timestamp}-%"
    count = await conn.fetchval(sequence_query, pattern)
    sequence = count + 1
    
    return f"{prefix}-{timestamp}-{sequence:04d}"

@router.post("/{request_id}/reject")
async def reject_onboarding_request(
    request_id: str,
    entity_type: str = Query(..., description="staff or entity"),
    reason: str = Query(..., description="Reason for rejection"),
    current_user = Depends(require_admin)
):
    """Reject an onboarding request"""
    try:
        conn = await get_db_connection()
        
        if entity_type == "staff":
            query = """
            UPDATE onboarding_requests 
            SET status = 'rejected', approved_by = $1, updated_at = $2
            WHERE id = $3 AND status = 'pending'
            """
            table = "onboarding_requests"
        else:
            query = """
            UPDATE onboarding_pending 
            SET status = 'rejected', reviewed_by = $1, reviewed_at = $2, remarks = $3
            WHERE id = $4 AND status = 'pending'
            """
            table = "onboarding_pending"
        
        now = datetime.now()
        result = await conn.execute(
            query, 
            uuid.UUID(current_user.id), 
            now, 
            reason if entity_type != "staff" else None,
            uuid.UUID(request_id)
        )
        
        await conn.close()
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Pending onboarding request not found")
        
        # Send rejection notification
        await notification_service.send_system_notification(
            title="Onboarding Request Rejected",
            message=f"Onboarding request {request_id} was rejected. Reason: {reason}",
            notification_type="warning",
            target_roles=["admin", "harvestflow_manager"]
        )
        
        return {
            "success": True,
            "message": f"Onboarding request rejected: {reason}"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rejecting onboarding request: {str(e)}")