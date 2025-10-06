from sqlalchemy import Column, String, Text, DateTime, Numeric, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from database import Base
import uuid

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("person_records.id", ondelete="CASCADE"), nullable=False, index=True)
    method = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    check_out_time = Column(DateTime(timezone=True))
    location = Column(Text, default="main_gate")
    verified_by = Column(UUID(as_uuid=True))
    override_reason = Column(Text)
    confidence_score = Column(Numeric)
    device_id = Column(Text, index=True)
    status = Column(Text, default="present")
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    person = relationship("PersonRecord", back_populates="attendance_logs")