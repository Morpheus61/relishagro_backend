# routes/__init__.py

from .auth import router as auth_router
from .admin import router as admin_router
from .workers import router as workers_router
from .job_types import router as job_types_router  # ✅ CHANGED FROM daily_job_types
from .provisions import router as provisions_router
from .onboarding import router as onboarding_router
from .attendance import router as attendance_router
from .face_recognition import router as face_recognition_router
from .gps_tracking import router as gps_tracking_router
from .supervisor import router as supervisor_router
from .yields import router as yields_router

__all__ = [
    'auth_router',
    'admin_router', 
    'workers_router',
    'job_types_router',
    'provisions_router',
    'onboarding_router',
    'attendance_router',
    'face_recognition_router',
    'gps_tracking_router',
    'supervisor_router',
    'yields_router'
]