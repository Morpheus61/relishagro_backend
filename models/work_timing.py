from sqlalchemy import Column, Text, Time, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid

class WorkTiming(Base):
    __tablename__ = "work_timings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location = Column(Text, nullable=False)
    timing_type = Column(Text, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())