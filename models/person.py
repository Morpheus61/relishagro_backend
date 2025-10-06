from sqlalchemy import Column, String, Text, Boolean, DateTime, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid

class PersonRecord(Base):
    __tablename__ = "person_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    full_name = Column(Text)
    contact_number = Column(Text)
    address = Column(Text)
    person_type = Column(Text, nullable=False, index=True)
    designation = Column(Text)
    firm_name = Column(Text)
    category = Column(Text)
    gst_number = Column(Text)
    status = Column(Text, default="active", index=True)
    
    # Face recognition
    face_embedding = Column(JSONB)
    face_registered_at = Column(DateTime(timezone=True))
    
    # Seasonal worker tracking
    employment_start_date = Column(DateTime(timezone=True))
    employment_end_date = Column(DateTime(timezone=True))
    is_seasonal_worker = Column(Boolean, default=False)
    
    # System tracking
    system_account_id = Column(UUID(as_uuid=True))
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    attendance_logs = relationship("AttendanceLog", back_populates="person")
    dispatches_as_driver = relationship("Dispatch", back_populates="driver", foreign_keys="[Dispatch.driver_id]")