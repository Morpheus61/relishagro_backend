from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # API
    API_VERSION: str = "v1"
    API_PREFIX: str = "/api"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # Face Recognition
    FACE_RECOGNITION_ENABLED: bool = True
    FACE_CONFIDENCE_THRESHOLD: float = 0.6
    FACE_STORAGE_PATH: str = "storage/faces"
    
    # GPS Tracking
    GPS_GEOFENCE_RADIUS_KM: float = 5.0
    GPS_TRACKING_INTERVAL_SECONDS: int = 60
    
    # Notifications
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    WHATSAPP_API_KEY: str = ""
    
    # Farm Location (for geofencing)
    FARM_LATITUDE: float = 8.2833  # Approximate for Kanyakumari
    FARM_LONGITUDE: float = 77.3167
    PROCESSING_UNIT_LATITUDE: float = 8.5241
    PROCESSING_UNIT_LONGITUDE: float = 76.9366
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()