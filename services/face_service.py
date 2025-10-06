import numpy as np
import cv2
import json
from typing import Optional, Tuple
from pathlib import Path
from config import settings

class FaceRecognitionService:
    """
    Lightweight face recognition using OpenCV Haar Cascades.
    Production-ready for low-connectivity mountain environments.
    """
    
    def __init__(self):
        self.available = False
        self.mode = "lightweight"
        self.face_cascade = None
        self._initialize()
    
    def _initialize(self):
        """Initialize OpenCV face detection"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.face_cascade.empty():
                raise Exception("Failed to load Haar cascade")
            
            # Ensure storage directory exists
            Path(settings.FACE_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
            
            self.available = True
            print("✅ Face Recognition Service initialized (Lightweight mode)")
        except Exception as e:
            print(f"⚠️ Face Recognition initialization failed: {e}")
            self.available = False
    
    def detect_face(self, image_data: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect face in image and return bounding box.
        Returns: (x, y, width, height) or None
        """
        if not self.available:
            return None
        
        try:
            gray = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) == 0:
                return None
            
            # Return largest face
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            return tuple(largest_face)
            
        except Exception as e:
            print(f"❌ Face detection error: {e}")
            return None
    
    def extract_embedding(self, image_data: np.ndarray) -> Optional[list]:
        """
        Extract face embedding (lightweight histogram-based features).
        Returns: 256-dimensional feature vector as list
        """
        if not self.available:
            return None
        
        try:
            face_box = self.detect_face(image_data)
            if face_box is None:
                return None
            
            x, y, w, h = face_box
            
            # Extract face region with padding
            padding = 20
            y1 = max(0, y - padding)
            y2 = min(image_data.shape[0], y + h + padding)
            x1 = max(0, x - padding)
            x2 = min(image_data.shape[1], x + w + padding)
            
            face_region = image_data[y1:y2, x1:x2]
            
            # Resize to standard size
            face_resized = cv2.resize(face_region, (64, 64))
            gray_face = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
            
            # Create histogram-based feature vector
            hist = cv2.calcHist([gray_face], [0], None, [256], [0, 256])
            hist = hist.flatten()
            
            # Normalize
            hist = hist / (np.sum(hist) + 1e-7)
            
            return hist.tolist()
            
        except Exception as e:
            print(f"❌ Embedding extraction error: {e}")
            return None
    
    def compare_embeddings(self, embedding1: list, embedding2: list) -> float:
        """
        Compare two face embeddings using histogram correlation.
        Returns: similarity score between 0 and 1
        """
        try:
            if len(embedding1) != len(embedding2):
                return 0.0
            
            arr1 = np.array(embedding1, dtype=np.float32)
            arr2 = np.array(embedding2, dtype=np.float32)
            
            # Correlation comparison (higher = more similar)
            similarity = cv2.compareHist(
                arr1,
                arr2,
                cv2.HISTCMP_CORREL
            )
            
            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            print(f"❌ Embedding comparison error: {e}")
            return 0.0
    
    def save_face_image(self, person_id: str, image_data: np.ndarray) -> Optional[str]:
        """
        Save face image to storage.
        Returns: file path or None
        """
        try:
            from datetime import datetime
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{person_id}_{timestamp}.jpg"
            filepath = Path(settings.FACE_STORAGE_PATH) / filename
            
            cv2.imwrite(str(filepath), image_data)
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Face image save error: {e}")
            return None