from .auth import router as auth_router
from .attendance import router as attendance_router
from .face_recognition import router as face_router
from .onboarding import router as onboarding_router
from .provisions import router as provisions_router
from .gps_tracking import router as gps_router
from .workers import router as workers_router          # ← ADD
from .job_types import router as job_types_router 

__all__ = [
    "auth_router",
    "attendance_router", 
    "face_router",
    "onboarding_router",
    "provisions_router",
    "gps_router",
    "workers_router",
    "job_types_router"
]