from sqlalchemy import Column, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from database import Base
import uuid

class OnboardingRequest(Base):
    __tablename__ = "onboarding_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    mobile = Column(Text)
    address = Column(Text)
    role = Column(Text)
    aadhaar = Column(Text)
    face_image = Column(Text)
    fingerprint_data = Column(Text)
    consent_given_at = Column(DateTime(timezone=True))
    status = Column(Text, default="pending", index=True)
    submitted_by = Column(UUID(as_uuid=True))
    approved_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())