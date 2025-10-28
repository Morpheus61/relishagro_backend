# routes/face_integration.py
"""
Integrated Face Recognition for Onboarding System
Updated to match Supabase schema column names
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from database import get_db_connection
import asyncpg
import uuid
import base64
import cv2
import numpy as np
from datetime import datetime
from services.face_service import FaceRecognitionService
from routes.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/face-integration", tags=["face_integration"])
face_service = FaceRecognitionService()


async def process_face_from_onboarding(
    person_id: str,
    face_image_base64: str,
    conn: asyncpg.Connection
) -> dict:
    """
    Extract face embedding from onboarding image and register it
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(face_image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {
                "success": False,
                "error": "Invalid image format"
            }
        
        # Extract face embedding (returns list)
        embedding = face_service.extract_embedding(img)
        
        if embedding is None:
            return {
                "success": False,
                "error": "No face detected in image"
            }
        
        # Save face image to file system
        image_path = face_service.save_face_image(person_id, img)
        
        # Update person record with embedding
        update_query = """
        UPDATE person_records 
        SET face_embedding = $1, 
            face_registered_at = $2,
            face_image_path = $3
        WHERE id = $4
        """
        
        await conn.execute(
            update_query,
            embedding,  # List stored as JSONB
            datetime.utcnow(),
            image_path,
            uuid.UUID(person_id)
        )
        
        return {
            "success": True,
            "embedding_length": len(embedding),
            "image_path": image_path,
            "mode": face_service.mode
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Face processing failed: {str(e)}"
        }


@router.post("/onboarding/{request_id}/approve-with-face")
async def approve_onboarding_with_face_registration(
    request_id: str,
    entity_type: str = Query(..., description="staff or entity"),
    current_user = Depends(require_admin)
):
    """
    Approve onboarding request AND automatically register face
    """
    try:
        conn = await get_db_connection()
        
        if entity_type == "staff":
            # Get onboarding request with face image
            request_query = """
            SELECT first_name, last_name, mobile, address, role, 
                   aadhaar, face_image
            FROM onboarding_requests 
            WHERE id = $1 AND status = 'pending'
            """
            
            request_data = await conn.fetchrow(request_query, uuid.UUID(request_id))
            
            if not request_data:
                await conn.close()
                raise HTTPException(status_code=404, detail="Pending staff onboarding request not found")
            
            # Generate staff ID
            staff_id = await generate_staff_id(conn, request_data['role'])
            
            # Create person record
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
            
            # Process face if image exists
            face_result = {"success": False, "error": "No face image provided"}
            if request_data['face_image']:
                face_result = await process_face_from_onboarding(
                    str(person_id),
                    request_data['face_image'],
                    conn
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
                    "onboarding_request_id": request_id,
                    "face_registered": face_result["success"],
                    "face_info": face_result
                },
                "message": "Staff onboarding approved" + (
                    " and face registered successfully" if face_result["success"] 
                    else f" but face registration failed: {face_result.get('error', 'Unknown error')}"
                )
            }
            
        else:
            await conn.close()
            raise HTTPException(status_code=501, detail="Entity onboarding with face not yet implemented")
            
    except HTTPException:
        raise
    except Exception as e:
        if 'conn' in locals():
            await conn.close()
        raise HTTPException(status_code=500, detail=f"Error in integrated approval: {str(e)}")


@router.post("/attendance/mark-with-face")
async def mark_attendance_with_face(
    image: str,  # Base64 encoded image
    location: str = "main_gate",
    device_id: str = None
):
    """
    Mark attendance using face recognition
    """
    if not face_service.available:
        return {
            "success": False,
            "authenticated": False,
            "error": "Face recognition service unavailable"
        }
    
    try:
        conn = await get_db_connection()
        
        # Decode image
        image_data = base64.b64decode(image)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            await conn.close()
            return {
                "success": False,
                "authenticated": False,
                "error": "Invalid image format"
            }
        
        # Extract face embedding
        query_embedding = face_service.extract_embedding(img)
        
        if query_embedding is None:
            await conn.close()
            return {
                "success": False,
                "authenticated": False,
                "error": "No face detected in image"
            }
        
        # Get all registered faces
        faces_query = """
        SELECT id, first_name, last_name, face_embedding, staff_id
        FROM person_records
        WHERE face_embedding IS NOT NULL 
        AND status = 'active'
        """
        
        persons = await conn.fetch(faces_query)
        
        if not persons:
            await conn.close()
            return {
                "success": False,
                "authenticated": False,
                "error": "No registered faces in database"
            }
        
        # Find best match
        best_match = None
        best_similarity = 0.0
        threshold = 0.6
        
        for person in persons:
            if person['face_embedding'] is None:
                continue
                
            stored_embedding = person['face_embedding']
            
            similarity = face_service.compare_embeddings(
                query_embedding,
                stored_embedding
            )
            
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = person
        
        if best_match:
            # Mark attendance - Use 'timestamp' column (not 'check_in_time')
            attendance_query = """
            INSERT INTO attendance_logs (
                person_id, method, timestamp, location, 
                confidence_score, device_id, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """
            
            now = datetime.now()
            attendance_id = await conn.fetchval(
                attendance_query,
                best_match['id'],
                'face',  # matches your CHECK constraint
                now,     # ✅ CORRECTED: Use 'timestamp' column
                location,
                float(best_similarity),
                device_id,
                'present',
                now
            )
            
            await conn.close()
            
            return {
                "success": True,
                "authenticated": True,
                "person_id": str(best_match['id']),
                "person_name": f"{best_match['first_name']} {best_match['last_name']}",
                "staff_id": best_match['staff_id'],
                "confidence": float(best_similarity),
                "attendance_id": str(attendance_id),
                "timestamp": now.isoformat(),
                "location": location,
                "mode": face_service.mode
            }
        else:
            await conn.close()
            return {
                "success": False,
                "authenticated": False,
                "confidence": float(best_similarity),
                "threshold": threshold,
                "error": "Face not recognized or confidence too low"
            }
            
    except Exception as e:
        if 'conn' in locals():
            await conn.close()
        return {
            "success": False,
            "authenticated": False,
            "error": f"Attendance marking failed: {str(e)}"
        }


async def generate_staff_id(conn, person_type: str) -> str:
    """Generate unique staff ID based on person type"""
    prefix_map = {
        'admin': 'ADM',
        'harvestflow_manager': 'HFM',
        'flavorcore_manager': 'FCM',
        'flavorcore_supervisor': 'FCS',
        'harvesting': 'HRV',
        'staff': 'STF',
        'supplier': 'SUP',
        'vendor': 'VND'
    }
    
    prefix = prefix_map.get(person_type, 'EMP')
    timestamp = datetime.now().strftime("%y%m%d")
    
    sequence_query = """
    SELECT COUNT(*) as count 
    FROM person_records 
    WHERE staff_id LIKE $1
    """
    pattern = f"{prefix}-{timestamp}-%"
    count = await conn.fetchval(sequence_query, pattern)
    sequence = count + 1
    
    return f"{prefix}-{timestamp}-{sequence:04d}"