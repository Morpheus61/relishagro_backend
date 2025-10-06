from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models import PersonRecord
from services import FaceRecognitionService
from utils import require_role
import cv2
import numpy as np
from typing import Optional
import uuid

router = APIRouter(prefix="/face", tags=["face_recognition"])
face_service = FaceRecognitionService()

@router.post("/register")
async def register_face(
    person_id: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: PersonRecord = Depends(require_role(["admin", "harvestflow_manager", "flavorcore_manager"]))
):
    """
    Register face for a person.
    Only managers and admin can register faces.
    """
    if not face_service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face recognition service unavailable"
        )
    
    try:
        # Read image
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format"
            )
        
        # Extract face embedding
        embedding = face_service.extract_embedding(img)
        if embedding is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in image"
            )
        
        # Get person record
        person = db.query(PersonRecord).filter(
            PersonRecord.id == uuid.UUID(person_id)
        ).first()
        
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Person not found"
            )
        
        # Save face image
        image_path = face_service.save_face_image(str(person.id), img)
        
        # Update person record with embedding
        person.face_embedding = embedding
        person.face_registered_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Face registered successfully",
            "person_id": str(person.id),
            "person_name": person.full_name,
            "embedding_length": len(embedding),
            "mode": face_service.mode
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face registration failed: {str(e)}"
        )

@router.post("/authenticate")
async def authenticate_face(
    image: UploadFile = File(...),
    location: str = Form("main_gate"),
    db: Session = Depends(get_db)
):
    """
    Authenticate person using face recognition.
    Public endpoint for attendance devices.
    """
    if not face_service.available:
        return {
            "authenticated": False,
            "error": "Face recognition service unavailable"
        }
    
    try:
        # Read image
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {
                "authenticated": False,
                "error": "Invalid image format"
            }
        
        # Extract query embedding
        query_embedding = face_service.extract_embedding(img)
        if query_embedding is None:
            return {
                "authenticated": False,
                "error": "No face detected in image"
            }
        
        # Get all registered faces
        persons = db.query(PersonRecord).filter(
            PersonRecord.face_embedding.isnot(None),
            PersonRecord.status == "active"
        ).all()
        
        if not persons:
            return {
                "authenticated": False,
                "error": "No registered faces in database"
            }
        
        # Compare with all registered faces
        best_match = None
        best_similarity = 0.0
        threshold = settings.FACE_CONFIDENCE_THRESHOLD
        
        for person in persons:
            similarity = face_service.compare_embeddings(
                query_embedding,
                person.face_embedding
            )
            
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = person
        
        if best_match:
            return {
                "authenticated": True,
                "person_id": str(best_match.id),
                "person_name": best_match.full_name,
                "confidence": float(best_similarity),
                "mode": face_service.mode
            }
        else:
            return {
                "authenticated": False,
                "confidence": float(best_similarity),
                "threshold": threshold,
                "error": "Face not recognized"
            }
            
    except Exception as e:
        return {
            "authenticated": False,
            "error": f"Authentication failed: {str(e)}"
        }