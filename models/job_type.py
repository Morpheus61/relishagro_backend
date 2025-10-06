from sqlalchemy import Column, Text, Numeric, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from database import Base
import uuid

class DailyJobType(Base):
    __tablename__ = "daily_job_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    unit_of_measurement = Column(Text)
    expected_output_per_worker = Column(Numeric)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())