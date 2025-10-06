from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    
    # Face Recognition
    FACE_RECOGNITION_ENABLED: bool = True
    FACE_CONFIDENCE_THRESHOLD: float = 0.6
    FACE_STORAGE_PATH: str = "storage/faces"
    
    # GPS Configuration
    GPS_GEOFENCE_RADIUS_KM: float = 5.0
    FARM_LATITUDE: float = 8.430153784606453
    FARM_LONGITUDE: float = 77.42507404406288
    PROCESSING_UNIT_LATITUDE: float = 8.097457521754535
    PROCESSING_UNIT_LONGITUDE: float = 77.550169800994
    
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # API Configuration
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields for Railway compatibility
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()